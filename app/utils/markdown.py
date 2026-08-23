"""Utilities for rendering review findings as GitHub-flavored Markdown."""
from typing import Dict, Any
import json

BOT_MARKER = "<!-- code-review-agent-comment -->"


def render_findings_markdown(response: Dict[str, Any]) -> str:
    """Render ReviewResponse into a markdown comment body.

    The body includes a hidden marker so the bot can find and update the
    same comment on subsequent runs. It also embeds the raw findings JSON
    in a hidden HTML comment for machine consumption if needed.
    """
    lines = [BOT_MARKER, "", f"## Code review: PR #{response.get('pr_number')}", ""]

    summary = response.get("summary")
    if summary:
        lines.append(summary)
        lines.append("")

    findings = response.get("findings", [])
    if not findings:
        lines.append("No findings.")
    else:
        lines.append("### Findings")
        lines.append("")
        for i, f in enumerate(findings, start=1):
            file = f.get("file", "unknown")
            line = f.get("line")
            loc = f"{file}:{line}" if line is not None else file
            lines.append(f"#### {i}. {loc} — **{f.get('severity', 'MEDIUM')}** ({f.get('category', 'unknown')})")
            lines.append(f"- **Issue:** {f.get('issue', '(no description)')}")
            lines.append(f"- **Suggestion:** {f.get('suggestion', '(no suggestion)')}")
            lines.append("")

    # Attach machine-readable payload
    try:
        payload = json.dumps(response.get("findings", []), indent=2)
    except Exception:
        payload = "[]"
    lines.append("<!-- findings-json")
    lines.append(payload)
    lines.append("-->")

    return "\n".join(lines)
