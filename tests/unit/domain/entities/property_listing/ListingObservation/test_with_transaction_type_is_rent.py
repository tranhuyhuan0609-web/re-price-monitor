def test_with_transaction_type_is_rent(observation_data):
    observation_data.listing.transaction_type = "rent"

    assert observation_data.price_per_m2 is None