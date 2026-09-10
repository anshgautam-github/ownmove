"""Small text helpers used by embedding and prompt assembly."""


def truncate(text: str, max_chars: int = 8000) -> str:
    """Guard against blowing the model context window."""
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "…"


def normalise_tags(tags: list[str] | None) -> list[str]:
    """Lowercase + de-duplicate while preserving order."""
    seen: set[str] = set()
    result: list[str] = []
    for tag in tags or []:
        key = tag.strip().lower()
        if key and key not in seen:
            seen.add(key)
            result.append(key)
    return result
