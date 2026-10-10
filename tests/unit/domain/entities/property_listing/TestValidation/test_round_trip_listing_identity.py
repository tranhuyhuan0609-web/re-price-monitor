from src.domain.entities.property_listing import ListingIdentity

def test_listing_identity_round_trip(identity_data):
    identity = ListingIdentity(**identity_data)

    data = identity.model_dump()
    restored = ListingIdentity.model_validate(data)

    assert restored.listing_key == identity.listing_key