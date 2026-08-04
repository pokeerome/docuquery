SUSPICIOUS_PATTERNS = [
    "ignore previous instructions",
    "ignore the above",
    "disregard previous",
    "disregard the above",
    "you are now",
    "new instructions:",
    "system prompt",
    "reveal your instructions",
    "ignore all prior",
    "override your instructions",
]


def flag_suspicious_content(text: str) -> list[str]:
    text_lower = text.lower()
    found = [pattern for pattern in SUSPICIOUS_PATTERNS if pattern in text_lower]
    return found