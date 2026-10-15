
import pytest
@pytest.fixture
def valid_config_data():
    return {
        "site_id": "batdongsan",
        "name": "Bat Dong San",
        "enabled": True,
        "base_url": "https://example.com",
        "start_urls": [
            "https://example.com/buy",
        ],
        "allowed_domains": [
            "example.com",
        ],
        "selectors": {
            "item": "div.listing",
            "url": "a.detail-link::attr(href)",
            "title": "a.detail-link::text",
            
        },
        "pagination": {
            "enabled": True,
            "next_page": "a.next::attr(href)",
            "max_pages": 10,
        },
        "crawler_settings": {
            "delay": 1.0,
            "randomize_delay": True,
            "concurrent_requests": 4,
            "download_timeout": 30.0,
            "retry_enabled": True,
            "max_retries": 3,
        },
    }
