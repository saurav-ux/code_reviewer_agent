"""Utilities for parsing unified diffs and extracting changed hunks.

This parser understands Git/patch unified hunk headers ("@@ -a,b +c,d @@")
and records added/removed lines with their line numbers in the new/old file
respectively. For backwards compatibility it also returns the previous
`diff` value containing joined added lines.
"""

from typing import Any, Dict, List
import re

HUNK_RE = re.compile(
    r"@@ -(?P<old_start>\d+)(?:,\d+)? \+(?P<new_start>\d+)(?:,\d+)? @@"
)


def parse_diff(diff_text: str) -> Dict[str, Any]:
    """Parse a unified diff string and return structured changed lines.

    Returns a dictionary with keys:
    - ``diff``: (str) joined added lines (compatibility)
    - ``changed_lines``: (list) entries like ``{ 'old_line': int|None, 'new_line': int|None, 'content': str, 'type': 'added'|'removed' }``
    """
    changed: List[Dict[str, Any]] = []
    added_lines_for_compat: List[str] = []

    cur_old: int | None = None
    cur_new: int | None = None

    for raw in (diff_text or "").splitlines():
        # Skip file header markers
        if raw.startswith("+++") or raw.startswith("---"):
            continue

        # Hunk header
        if raw.startswith("@@"):
            m = HUNK_RE.search(raw)
            if m:
                cur_old = int(m.group("old_start"))
                cur_new = int(m.group("new_start"))
            else:
                cur_old = None
                cur_new = None
            continue

        if not raw:
            # Empty line within a hunk is a context line (counts as one for both)
            if cur_old is not None and cur_new is not None:
                cur_old += 1
                cur_new += 1
            continue

        prefix = raw[0]
        content = raw[1:]

        if prefix == " ":
            # Context line: advance both counters
            if cur_old is not None:
                cur_old += 1
            if cur_new is not None:
                cur_new += 1
            continue

        if prefix == "+":
            # Added line: record with the new-file line number
            if cur_new is not None:
                changed.append(
                    {
                        "old_line": None,
                        "new_line": cur_new,
                        "content": content.rstrip("\n"),
                        "type": "added",
                    }
                )
                added_lines_for_compat.append(content.lstrip())
                cur_new += 1
            else:
                # No hunk context; still record without line number
                changed.append(
                    {
                        "old_line": None,
                        "new_line": None,
                        "content": content.rstrip("\n"),
                        "type": "added",
                    }
                )

        elif prefix == "-":
            # Removed line: record with the old-file line number
            if cur_old is not None:
                changed.append(
                    {
                        "old_line": cur_old,
                        "new_line": None,
                        "content": content.rstrip("\n"),
                        "type": "removed",
                    }
                )
                cur_old += 1
            else:
                changed.append(
                    {
                        "old_line": None,
                        "new_line": None,
                        "content": content.rstrip("\n"),
                        "type": "removed",
                    }
                )

        else:
            # Unknown prefix (could be binary markers or other metadata) — ignore
            continue

    return {"diff": "\n".join(added_lines_for_compat), "changed_lines": changed}
