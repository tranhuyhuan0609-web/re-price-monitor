import hashlib
def create_url_hash(url: str) -> str:
    """Create a SHA-256 hash from a normalized URL."""
    if not isinstance(url, str) or not url.strip():
        raise ValueError("url must be a non-empty string")

    return hashlib.sha256(url.encode("utf-8")).hexdigest()
