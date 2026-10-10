from src.domain.entities.property_listing import ListingIdentity
from pydantic import ValidationError
import pytest
def test_listing_identity_rejects_unknown_field(identity_data):
    data = {
        **identity_data,
        "unknown_field": "unexpected",
    }

    with pytest.raises(ValidationError):
        ListingIdentity(**data)