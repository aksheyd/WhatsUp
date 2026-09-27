from __future__ import annotations

import re

SCRAPED_CHARS = 12_000
PROMPT_CHARS = 8_000
PUBLISHED_CHARS = 2_000
MIN_CHARS = 800

TOC_CHROME = re.compile(
    r"browse table of contents|share link to section|instruction sheet|"
    r"this code of ordinances and/or any other documents that appear on this site",
    re.I,
)


def cap(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0] + "…"


def is_usable(text: str) -> bool:
    """True when the text reads like ordinance text rather than a table of contents or page chrome."""
    compact = " ".join(text.split())
    if len(compact) < MIN_CHARS:
        return False
    return not (TOC_CHROME.search(compact) and len(compact) < 4000)
