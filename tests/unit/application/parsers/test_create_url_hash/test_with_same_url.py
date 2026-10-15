from src.application.parsers.create_url_hash import create_url_hash
def test_create_url_hash_with_same_url():
    url1 = "https://example.com/property/123"
    url2 = "https://example.com/property/123"
    hash1 = create_url_hash(url1)
    hash2 = create_url_hash(url2)
    assert hash1 == hash2