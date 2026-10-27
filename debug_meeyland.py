
import scrapy
from scrapy.crawler import CrawlerProcess


class MeeylandDebugSpider(scrapy.Spider):
    name = "meeyland_debug"

    start_urls = [
        "https://meeyland.com/ban-nha-rieng-ha-noi-h122"
    ]

    custom_settings = {
        "LOG_LEVEL": "INFO",
        "RETRY_ENABLED": False,
        "DOWNLOAD_TIMEOUT": 30,
    }

    def parse(self, response):
        self.logger.info(
            "DEBUG status=%s bytes=%s url=%s",
            response.status,
            len(response.body),
            response.url,
        )
        self.logger.info(
            "DEBUG headers=%r",
            dict(response.headers),
        )
        self.logger.info(
            "DEBUG html_prefix=%r",
            response.text[:200],
        )


process = CrawlerProcess()
process.crawl(MeeylandDebugSpider)
process.start()
