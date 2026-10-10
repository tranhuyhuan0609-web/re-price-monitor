from src.domain.entities.property_listing import PriceInformation
from decimal import Decimal
import pytest
from pydantic import ValidationError
def test_contract_but_have_amount():
    with pytest.raises(ValidationError):
        PriceInformation(
            amount=Decimal("3500000000"),
            currency="VND",
            price_vnd=Decimal("3500000000"),
            fx_rate=None,
            fx_rate_at=None,
            status="contract",
        )