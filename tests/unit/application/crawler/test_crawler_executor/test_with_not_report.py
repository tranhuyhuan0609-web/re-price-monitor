
from src.application.crawler.crawl_run_result import CrawlStatus
from src.application.crawler.crawler_executor import CrawlExecutionReport
from src.application.crawler.crawler_runner import CrawlerRunner
from src.domain.entities.crawler_config import CrawlerConfig


class FakeCrawlerExecutor:
    def __init__(self, report: CrawlExecutionReport) -> None:
        self.report = report
        self.received_config = None
        self.received_crawl_run_id = None
        self.execute_call_count = 0

    def execute(
        self,
        config: CrawlerConfig,
        crawl_run_id: str,
    ) -> CrawlExecutionReport:
        self.execute_call_count += 1
        self.received_config = config
        self.received_crawl_run_id = crawl_run_id
        return self.report


def test_runner_works_with_fake_crawler_executor(valid_config_data):
    config = CrawlerConfig(**valid_config_data)

    report = CrawlExecutionReport(
        items_scraped=5,
        finish_reason="finished",
        request_failures=0,
    )
    executor = FakeCrawlerExecutor(report)

    runner = CrawlerRunner(
        executor=executor,
        run_id_factory=lambda: "crawl-run-013",
    )

    result = runner.run(config)

    assert result.status == CrawlStatus.SUCCESS
    assert result.crawl_run_id == "crawl-run-013"

    assert executor.execute_call_count == 1
    assert executor.received_config is config
    assert executor.received_crawl_run_id == "crawl-run-013"
