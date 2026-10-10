
from decimal import Decimal

def test_price_per_m2_for_sale_with_total_price(observation_data):

    assert observation_data.price_per_m2 == Decimal("50000000")