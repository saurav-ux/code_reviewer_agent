"""Utilities for parsing diffs and extracting changed hunks."""

from typing import Dict


def parse_diff(diff_text: str) -> Dict[str, str]:
    """Very small parser: extract added lines from a GitHub patch.

    Returns a dict with a `diff` key containing the joined added lines
    with the leading '+' removed.
    """
    lines = []
    for raw in (diff_text or "").splitlines():
        if raw.startswith("+++"):
            continue
        if raw.startswith("@@"):
            continue
        if raw.startswith("+") and not raw.startswith("+++"):
            # Strip leading '+' and any leading whitespace
            lines.append(raw[1:].lstrip())

    return {"diff": "\n".join(lines)}
