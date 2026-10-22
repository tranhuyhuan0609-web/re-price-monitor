import re

_EMOJI_RE = re.compile(
    "[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF\U0001F900-\U0001F9FF\U0001FA70-\U0001FAFF"
    "\U00002700-\U000027BF\U0001F1E6-\U0001F1FF]+"
)

def remove_emoji_and_clean(text: str | None) -> str | None:
    if not text:
        return None
    
    text = _EMOJI_RE.sub("", text)
    cleaned = text.strip()
    
    return cleaned or None
