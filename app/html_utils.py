from __future__ import annotations

import html
import re


STYLE_RE = re.compile(r"<style[^>]*>.*?</style>", re.IGNORECASE | re.DOTALL)
SCRIPT_RE = re.compile(r"<script[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL)
BLOCK_TAG_RE = re.compile(r"</?(?:p|br|li|div|tr|td|th|ul|ol)[^>]*>", re.IGNORECASE)
TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"\s+")


def strip_html(value: str | None) -> str:
    if not value:
        return ""
    text = html.unescape(value)
    text = STYLE_RE.sub(" ", text)
    text = SCRIPT_RE.sub(" ", text)
    text = BLOCK_TAG_RE.sub(" | ", text)
    text = TAG_RE.sub(" ", text)
    text = text.replace("\r", " ").replace("\n", " ")
    return SPACE_RE.sub(" ", text).strip()
