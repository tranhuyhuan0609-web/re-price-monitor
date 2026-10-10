from src.domain.entities.property_listing import PriceInformation
from decimal import Decimal
from pydantic import ValidationError
import pytest
def test_not_vnd_not_have_fx_rate():
    with pytest.raises(ValidationError):
        PriceInformation(
            amount=Decimal("150000"),
            currency="USD",
            price_vnd=Decimal("3500000000"),
            fx_rate=None,
            fx_rate_at=None,
            status="known",
        )