from __future__ import annotations
import re
import unicodedata
from dataclasses import dataclass, replace
from decimal import ROUND_HALF_UP, Decimal
from urllib.parse import urlsplit
MAX_VND = Decimal("1000000000000")
_BARE_VND_THRESHOLD = Decimal("1000000")
_MAX_AREA_M2 = Decimal("1000000000")
_RENT_TITLE_RE = re.compile(r"^[\W_]*(?:cần\s+|can\s+)?cho\s+thu[eê]\b")
_NOT_LETTER = r"(?![^\W\d_])" 

_CONTACT_TERMS = (
    "thỏa thuận", "thoả thuận", "thoa thuan",
    "liên hệ", "lien he", "contact",
)
_NEGOTIABLE_TERMS = ("thương lượng", "thuong luong")
_UNIT_MULTIPLIER: dict[str, Decimal] = {
    "tỷ": Decimal("1000000000"),
    "tỉ": Decimal("1000000000"),
    "ty": Decimal("1000000000"),
    "triệu": Decimal("1000000"),
    "trieu": Decimal("1000000"),
    "tr": Decimal("1000000"),
    "nghìn": Decimal("1000"),
    "nghin": Decimal("1000"),
    "ngàn": Decimal("1000"),
    "ngan": Decimal("1000"),
    "k": Decimal("1000"),
}
_BILLION_UNITS = frozenset({"tỷ", "tỉ", "ty"})

_TOKEN_RE = re.compile(
    r"(?P<num>\d+(?:[.,]\d+)*)\s*"
    r"(?:(?P<unit>triệu|trieu|tr|tỷ|tỉ|ty|nghìn|nghin|ngàn|ngan|k)"
    + _NOT_LETTER
    + r")?"
)
_VND_MARKER_RE = re.compile(r"₫|vnđ|vnd|đồng|đ" + _NOT_LETTER)
_USD_RE = re.compile(r"usd|us\$|\$|đô la|do la")
_QUALIFIER_RE = re.compile(
    r"/|\btrên\b|\btren\b|\bmỗi\b|\bmoi\b|\bper\b|\bm2\b|m²"
)
_PER_M2_RE = re.compile(r"\bm2\b|m²|mét vuông|met vuong|\bsqm\b")
_PERIOD_PREFIX = r"(?:/|\btrên\b|\btren\b|\bper\b|\bmỗi\b|\bmoi\b)\s*"
_PER_MONTH_RE = re.compile(
    _PERIOD_PREFIX + r"(?:tháng|thang|th|month|mo)" + _NOT_LETTER
    + r"|\bmonthly\b|\bhàng tháng\b|\bhang thang\b"
)
_PER_YEAR_RE = re.compile(
    _PERIOD_PREFIX + r"(?:năm|nam|year|yr)" + _NOT_LETTER
)

_RANGE_SEPARATOR_RE = re.compile(r"^\s*(?:-|–|—|~|đến|đên|tới|toi|to)\s*$")
_SCIENTIFIC_RE = re.compile(r"(?<![^\W\d_])\d+(?:[.,]\d+)?e[+-]?\d+")


@dataclass(frozen=True, slots=True)
class ParsedPrice:
    amount: Decimal | None
    currency: str | None
    status: str
    basis: str = "total"     
    per_month: bool = False   

def _normalize(value: str) -> str:
    return unicodedata.normalize("NFC", value).lower().strip()


def _parse_number(token: str, unit: str | None) -> Decimal:

    if re.fullmatch(r"\d+", token):
        return Decimal(token)
    if unit in _BILLION_UNITS and re.fullmatch(r"\d{1,3}[.,]\d{3}", token):
        return Decimal(token.replace(",", "."))
    if re.fullmatch(r"[1-9]\d{0,2}(?:[.,]\d{3})+", token):
        return Decimal(re.sub(r"[.,]", "", token))  
    if re.fullmatch(r"[1-9]\d{0,2}(?:\.\d{3})+,\d+", token):
        return Decimal(token.replace(".", "").replace(",", "."))  
    if re.fullmatch(r"[1-9]\d{0,2}(?:,\d{3})+\.\d+", token):
        return Decimal(token.replace(",", "")) 
    if re.fullmatch(r"\d+[.,]\d+", token):
        return Decimal(token.replace(",", "."))  
    raise ValueError(f"cannot parse number: {token!r}")


def _sum_tokens(
    tokens: list[tuple[str, str | None]],
    *,
    bare_is_amount: bool,
    vnd_marker: bool,
    require_unit: bool,
) -> Decimal:
    total = Decimal(0)
    previous: Decimal | None = None
    for index, (number, unit) in enumerate(tokens):
        if unit is not None:
            multiplier = _UNIT_MULTIPLIER[unit]
            total += _parse_number(number, unit) * multiplier
            previous = multiplier
        elif index > 0 and previous is not None and re.fullmatch(r"\d{1,3}", number):
            total += Decimal("0." + number) * previous
            previous = None
        elif index == 0 and not require_unit:
            value = _parse_number(number, None)
            if not (bare_is_amount or vnd_marker or value >= _BARE_VND_THRESHOLD):
                raise ValueError(
                    f"ambiguous price without a unit: {number!r}"
                )
            total += value
        else:
            raise ValueError(f"unexpected number in price: {number!r}")
    return total

def _tokenize(text: str) -> list[tuple[str, str | None]]:
    matches = list(_TOKEN_RE.finditer(text))
    if not matches:
        raise ValueError(f"cannot parse numeric value: {text!r}")
    if len(matches) >= 2:
        first, second = matches[0], matches[1]
        gap = text[first.end():second.start()]
        if _RANGE_SEPARATOR_RE.match(gap):
            return [(first.group("num"), first.group("unit") or second.group("unit"))]

    return [(m.group("num"), m.group("unit")) for m in matches]


def parse_price(value: str | None) -> ParsedPrice:

    if not value or not value.strip():
        return ParsedPrice(None, None, "contact")

    text = _normalize(value)
    if any(term in text for term in _CONTACT_TERMS):
        return ParsedPrice(None, None, "contact")

    if _SCIENTIFIC_RE.search(text):
            return ParsedPrice(None, None, "contact")

    if _PER_YEAR_RE.search(text):
        raise ValueError(f"unsupported price period (per year): {value!r}")

    per_month = bool(_PER_MONTH_RE.search(text))
    basis = "per_m2" if _PER_M2_RE.search(text) else "total"

    cut = _QUALIFIER_RE.search(text)
    amount_text = text[: cut.start()] if cut else text

    negotiable = any(term in text for term in _NEGOTIABLE_TERMS)
    is_usd = bool(_USD_RE.search(text))
    vnd_marker = bool(_VND_MARKER_RE.search(amount_text))

    try:
        amount = _sum_tokens(
            _tokenize(amount_text),
            bare_is_amount=is_usd,
            vnd_marker=vnd_marker,
            require_unit=negotiable and not is_usd and not vnd_marker,
        )
    except ValueError:
        if negotiable:
            return ParsedPrice(None, None, "contact")
        raise

    if amount <= 0:
        return ParsedPrice(None, None, "contact")
    if amount > MAX_VND:
        raise ValueError(f"implausible price: {value!r}")

    if is_usd:
        return ParsedPrice(
            amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            "USD", "known", basis, per_month,
        )
    return ParsedPrice(
        amount.quantize(Decimal("1"), rounding=ROUND_HALF_UP),
        "VND", "known", basis, per_month,
    )

def parse_area_m2(value: str | None) -> Decimal | None:
   
    if not value or not value.strip():
        return None
    text = _normalize(value)
    if _SCIENTIFIC_RE.search(text):
        return None
    match = re.search(r"\d+(?:[.,]\d+)*", _normalize(value))
    if match is None:
        raise ValueError(f"cannot parse area: {value!r}")
    area = _parse_number(match.group(), None)
    if area > _MAX_AREA_M2:
        raise ValueError(f"implausible area: {value!r}")
    area = area.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if area <= 0:
        return None 
    return area


def _first_path_segment(url: str | None) -> str:
    if not url:
        return ""
    try:
        path = urlsplit(url).path
    except ValueError:
        return ""
    return path.strip("/").split("/", 1)[0].lower()


def detect_transaction_type(
    *,
    per_month: bool,
    title: str | None,
    url: str | None,
    page_url: str | None,
) -> tuple[str, bool]:
    if per_month:
        return "rent", False

    if title and _RENT_TITLE_RE.search(_normalize(title)):
        return "rent", True

    page_segment = _first_path_segment(page_url)
    url_segment = _first_path_segment(url)
    if (
        "cho-thue" in page_segment
        or page_segment.startswith("thue-")
        or url_segment.startswith(("cho-thue", "thue-"))
    ):
        return "rent", True

    return "sale", False


def to_monthly_rent(
    price: ParsedPrice,
    area_m2: Decimal | None,
) -> tuple[ParsedPrice, str | None]:
    if price.status != "known":
       return replace(price, basis="per_month"), None
    if price.basis == "per_m2":
        if not area_m2:
            return (
                ParsedPrice(None, None, "contact", "per_month", True),
                "rent_price_per_m2_without_area",
            )
        quantum = Decimal("1") if price.currency == "VND" else Decimal("0.01")
        total = (price.amount * area_m2).quantize(quantum, rounding=ROUND_HALF_UP)
        if price.currency == "VND" and total > MAX_VND:
            raise ValueError("implausible monthly rent")
        return replace(price, amount=total, basis="per_month"), None
    return replace(price, basis="per_month"), None
