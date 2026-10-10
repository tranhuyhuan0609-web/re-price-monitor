def test_with_area_is_none(observation_data):
    observation_data.details.area_m2 = None

    assert observation_data.price_per_m2 is None