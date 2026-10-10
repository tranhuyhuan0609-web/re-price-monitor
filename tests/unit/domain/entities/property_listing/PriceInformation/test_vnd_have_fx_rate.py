from src.domain.entities.property_listing import PriceInformation
from pydantic import ValidationError
from decimal import Decimal
import pytest
def test_vnd_have_fx_rate():
    with pytest.raises(ValidationError):
        PriceInformation(
            amount=Decimal("3500000000"),
            currency="VND",
            price_vnd=Decimal("3500000000"),
            fx_rate=Decimal("0.000043"),
            fx_rate_at="2023-01-01T00:00:00Z",
            status="known",
        )