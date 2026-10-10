from src.domain.entities.property_listing import ListingIdentity
from pydantic import ValidationError
import pytest
def test_listing_identity_rejects_invalid_url_hash(identity_data):
    data = {
        **identity_data,
        "url_hash": "invalid_url_hash",
    }

    with pytest.raises(ValidationError):
        ListingIdentity(**data)