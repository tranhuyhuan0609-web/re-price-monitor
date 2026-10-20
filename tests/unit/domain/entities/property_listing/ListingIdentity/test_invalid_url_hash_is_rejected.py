from src.domain.entities.property_listing import ListingIdentity
import pytest
from pydantic import ValidationError
def test_invalid_url_hash_is_rejected():
    with pytest.raises(ValidationError):
        ListingIdentity(
            source="test-source",
            url="https://example.com/listing/12345",
            url_hash="invalid-hash",  
        )