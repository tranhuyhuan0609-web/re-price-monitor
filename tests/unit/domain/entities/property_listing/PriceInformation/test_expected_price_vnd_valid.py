from src.domain.entities.property_listing import PriceInformation
from decimal import Decimal
def test_expected_price_vnd_valid():
    price_info = PriceInformation(
        amount=Decimal("35"),
        currency="USD",
        price_vnd=Decimal("805000"),
        fx_rate=Decimal("23000"),
        fx_rate_at="2023-01-01T00:00:00Z",
        status="known",
    )
