import pytest
from src.infrastructure.crawler import scrapy_worker
def test_build_scrapy_settings_returns_expected_values(
    monkeypatch,
    valid_config_data,
):
    # Arrange
    config = scrapy_worker.CrawlerConfig.model_validate(valid_config_data)

    # Giả lập pipeline đã được cấu hình để test phần settings
    monkeypatch.setattr(
        scrapy_worker,
        "ITEM_PIPELINES",
        {"tests.fakes.FakePipeline": 300},
    )

    # Act
    settings = scrapy_worker._build_scrapy_settings(
        config,
        closespider_timeout=600,
    )

    # Assert
    assert settings["ROBOTSTXT_OBEY"] is True
    assert settings["DOWNLOAD_DELAY"] == config.crawler_settings.delay
    assert (
        settings["CONCURRENT_REQUESTS"]
        == config.crawler_settings.concurrent_requests
    )
    assert settings["CLOSESPIDER_TIMEOUT"] == 600
    assert settings["ITEM_PIPELINES"] == {"tests.fakes.FakePipeline": 300}
def test_build_scrapy_settings_raises_not_item_pipeline_configured(
    monkeypatch,
    valid_config_data,
):
    # Arrange
    config = scrapy_worker.CrawlerConfig.model_validate(valid_config_data)

    # Giả lập pipeline chưa được cấu hình
    monkeypatch.setattr(scrapy_worker, "ITEM_PIPELINES", {})

    # Act & Assert
    with pytest.raises(NotImplementedError) as e:
        scrapy_worker._build_scrapy_settings(
            config,
            closespider_timeout=600,
        )
    assert (str(e.value) == "No item pipeline configured; refusing to discard scraped items."
    )