from src.domain.entities.raw_event import RawEventBuildError
import pytest
from src.domain.entities.raw_event import normalize_url
def test_normalize_url():
    url = "https://www.example.com/path/to/resource?query=param#fragment"
    normalized = normalize_url(url)
    assert normalized == "https://www.example.com/path/to/resource?query=param"

    url = "HTTPS://EXAMPLE.COM:443/listing/123"
    normalized = normalize_url(url)
    assert normalized == "https://example.com/listing/123"
def test_normalize_url_with_invalid_url():
    url = "ftp://example.com/file"
    with pytest.raises(RawEventBuildError):
        normalize_url(url)