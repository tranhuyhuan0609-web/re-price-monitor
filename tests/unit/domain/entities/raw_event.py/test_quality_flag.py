from src.domain.entities.raw_event import _normalize_flags
def test_normalize_flags():
    flags = ["missing_price", "missing_price", "invalid_area"]
    normalized = _normalize_flags(flags)    
    assert normalized == ("invalid_area", "missing_price")
   