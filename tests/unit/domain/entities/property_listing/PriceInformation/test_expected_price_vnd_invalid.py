from src.domain.entities.property_listing import PriceInformation
from decimal import Decimal
import pytest
from pydantic import ValidationError
def test_expected_price_vnd_invalid():
    with pytest.raises(ValidationError):
        PriceInformation(
            amount=Decimal("35"),
            currency="USD",
            price_vnd=Decimal("3500000000"),
            fx_rate=Decimal("23000"),
            fx_rate_at="2023-01-01T00:00:00Z",
            status="known",
        )