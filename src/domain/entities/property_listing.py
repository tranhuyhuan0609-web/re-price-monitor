
from decimal import Decimal, ROUND_HALF_UP
from typing import Literal

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    computed_field,
    field_validator,
    model_validator,
)


INACTIVE_AFTER_MISSES = 5


class DomainModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    @model_validator(mode="before")
    @classmethod
    def remove_computed_fields(cls, data):
        if not isinstance(data, dict):
            return data

        computed_names = cls.model_computed_fields.keys()
        return {
            key: value
            for key, value in data.items()
            if key not in computed_names
        }


class ListingIdentity(DomainModel):
    source: str = Field(min_length=1)
    url: HttpUrl
    url_hash: str = Field(pattern=r"^[0-9a-f]{64}$")

    @field_validator("source")
    @classmethod
    def normalize_source(cls, value: str) -> str:
        return value.lower()

    @computed_field
    @property
    def listing_key(self) -> str:
        return f"{self.source}:url:{self.url_hash}"

class ListingInformation(DomainModel):
    title: str = Field(min_length=1)
    transaction_type: Literal["sale", "rent"]
class LocationInformation(DomainModel):
    address: str | None = None
class PropertyDetails(DomainModel):
    area_m2: Decimal | None = Field(default=None, gt=0)
class PriceInformation(DomainModel):
    status: Literal["known", "contact", "negotiable"] = "known"

    basis: Literal["total", "per_m2", "per_month"] = "total"

    amount: Decimal | None = Field(default=None, gt=0)
    currency: str | None = Field(
        default=None,
        pattern=r"^[A-Z]{3}$",
    )

    price_vnd: Decimal | None = Field(default=None, gt=0)
    @model_validator(mode="after")
    def validate_price(self):
        monetary_values = (
            self.amount,
            self.currency,
            self.price_vnd,
        )

        if self.status != "known":
            if any(value is not None for value in monetary_values):
                raise ValueError(
                    "Unknown, contact, or negotiable prices "
                    "must not contain monetary values."
                )
            return self

        if self.amount is None or self.currency is None:
            raise ValueError(
                "Known prices require amount and currency."
            )

        if self.currency == "VND":

            if (
                self.price_vnd is not None
                and self.price_vnd != self.amount
            ):
                raise ValueError(
                    "For VND, price_vnd must equal amount."
                )

            self.price_vnd = self.amount
            return self

class ListingObservation(DomainModel):
    identity: ListingIdentity
    listing: ListingInformation
    price: PriceInformation

    location: LocationInformation = Field(
        default_factory=LocationInformation
    )
    details: PropertyDetails = Field(
        default_factory=PropertyDetails
    )

    crawled_at: AwareDatetime
    raw_event_id: str = Field(min_length=1)
    quality_flags: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_transaction_price_basis(self):
        if (
            self.listing.transaction_type == "sale"
            and self.price.basis == "per_month"
        ):
            raise ValueError(
                "Sale listings cannot use basis='per_month'."
            )

        return self

    @computed_field
    @property
    def price_per_m2(self) -> Decimal | None:
        price = self.price
        area = self.details.area_m2

        if self.listing.transaction_type != "sale":
            return None

        if price.status != "known" or price.price_vnd is None:
            return None

        if price.basis == "per_m2":
            value = price.price_vnd
        elif price.basis == "total" and area is not None:
            value = price.price_vnd / area
        else:
            return None

        return value.quantize(
            Decimal("1"),
            rounding=ROUND_HALF_UP,
        )

class ListingLifecycle(DomainModel):
    listing_key: str = Field(min_length=1)
    status: Literal["active", "inactive"] = "active"
    missing_count: int = Field(default=0, ge=0)

    last_seen_at: AwareDatetime
    ended_at: AwareDatetime | None = None

    @model_validator(mode="after")
    def validate_lifecycle(self):
        if self.status == "active":
            if self.missing_count >= INACTIVE_AFTER_MISSES:
                raise ValueError(
                    "Active listings must have fewer than "
                    f"{INACTIVE_AFTER_MISSES} misses."
                )

            if self.ended_at is not None:
                raise ValueError(
                    "Active listings must not have ended_at."
                )

            return self

        if self.missing_count < INACTIVE_AFTER_MISSES:
            raise ValueError(
                "Inactive listings must reach the missing threshold."
            )

        if self.ended_at is None:
            raise ValueError(
                "Inactive listings require ended_at."
            )

        if self.ended_at < self.last_seen_at:
            raise ValueError(
                "ended_at cannot be earlier than last_seen_at."
            )

        return self