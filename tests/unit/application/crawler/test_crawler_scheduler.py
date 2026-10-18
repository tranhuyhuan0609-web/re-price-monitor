import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from src.application.crawler.crawl_run_result import CrawlRunResult, CrawlStatus
from src.application.crawler.crawler_scheduler import CrawlerScheduler


def _result(site_id: str) -> CrawlRunResult:
    now = datetime.now(timezone.utc)
    return CrawlRunResult(
        crawl_run_id=f"run-{site_id}",
        status=CrawlStatus.SUCCESS,
        started_at=now,
        finished_at=now,
    )


@pytest.mark.asyncio
async def test_scheduler_runs_enabled_configs_in_one_tick(valid_config_data):
    from src.domain.entities.crawler_config import CrawlerConfig

    valid_config = CrawlerConfig.model_validate(valid_config_data)
    repository = type(
        "Repository",
        (),
        {"get_enabled_configs": lambda self: asyncio.sleep(0, result=[valid_config])},
    )()
    seen = []

    async def run_site(config):
        seen.append(config.site_id)
        return _result(config.site_id)

    results = await CrawlerScheduler(
        config_repository=repository,
        run_site=run_site,
        max_concurrency=1,
    ).run_once()

    assert seen == [valid_config.site_id]
    assert len(results) == 1


@pytest.mark.asyncio
async def test_scheduler_limits_concurrency(valid_config_data):
    from src.domain.entities.crawler_config import CrawlerConfig

    configs = [
        CrawlerConfig.model_validate(
            {**valid_config_data, "site_id": f"site-{index}"}
        )
        for index in range(3)
    ]
    repository = type(
        "Repository",
        (),
        {"get_enabled_configs": lambda self: asyncio.sleep(0, result=configs)},
    )()
    active = 0
    peak = 0

    async def run_site(config):
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        await asyncio.sleep(0)
        active -= 1
        return _result(config.site_id)

    await CrawlerScheduler(
        config_repository=repository,
        run_site=run_site,
        max_concurrency=2,
    ).run_once()

    assert peak <= 2


@pytest.mark.asyncio
async def test_scheduler_skips_site_until_interval_elapsed(valid_config_data):
    from src.domain.entities.crawler_config import CrawlerConfig

    config = CrawlerConfig.model_validate({
        **valid_config_data,
        "schedule_interval_seconds": 60,
    })
    repository = type(
        "Repository",
        (),
        {"get_enabled_configs": lambda self: asyncio.sleep(0, result=[config])},
    )()
    current = [datetime(2026, 1, 1, tzinfo=timezone.utc)]
    calls = 0

    async def run_site(site_config):
        nonlocal calls
        calls += 1
        return _result(site_config.site_id)

    scheduler = CrawlerScheduler(
        config_repository=repository,
        run_site=run_site,
        clock=lambda: current[0],
    )
    await scheduler.run_once()
    await scheduler.run_once()
    assert calls == 1

    current[0] += timedelta(seconds=60)
    await scheduler.run_once()
    assert calls == 2
