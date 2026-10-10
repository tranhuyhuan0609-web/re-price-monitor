from src.domain.entities.property_listing import PriceInformation
from decimal import Decimal
def test_vnd_price_defaults_price_vnd():
    price_info = PriceInformation(
        amount=Decimal("3500000000"),
        currency="VND",
     
        fx_rate=None,
        fx_rate_at=None,
        status="known",
    )


    
    assert price_info.amount == Decimal("3500000000")
    assert price_info.currency == "VND"
    assert price_info.price_vnd == Decimal("3500000000")
    assert price_info.fx_rate is None
    assert price_info.fx_rate_at is None
    assert price_info.status == "known"