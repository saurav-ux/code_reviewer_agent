"""Summarize node: create a final summary of findings."""

import logging
from typing import Dict, Any

from app.graph.state import ReviewState

logger = logging.getLogger("code_review_agent.summarize")


def summarize_findings(state: ReviewState) -> Dict[str, Any]:
    """Summarize review findings into a human-readable format.
    
    Converts the structured findings into a detailed summary text that includes
    counts and a short per-finding description (file, line, severity, category,
    issue, suggestion).
    
    Args:
        state: Current ReviewState containing review_findings
    
    Returns:
        Updated state with final_summary
    """
    findings = state.get("review_findings", [])
    review_error = state.get("review_error")
    logger.info(f"Summarizing {len(findings)} findings")

    if review_error:
        summary = f"Code review failed: {review_error}"
        logger.error(summary)
        return {"final_summary": summary}

    if not findings:
        summary = "No issues found. Code review passed."
        logger.info("No findings - code review passed")
        return {"final_summary": summary}

    # Count by severity
    high_count = sum(1 for f in findings if f.get("severity") == "HIGH")
    medium_count = sum(1 for f in findings if f.get("severity") == "MEDIUM")
    low_count = sum(1 for f in findings if f.get("severity") == "LOW")

    # Count by category
    categories = {}
    for finding in findings:
        cat = finding.get("category", "unknown")
        categories[cat] = categories.get(cat, 0) + 1

    # Header with totals
    summary_lines = [f"Code review found {len(findings)} issue(s):"]
    if high_count:
        summary_lines.append(f"  • {high_count} HIGH severity")
    if medium_count:
        summary_lines.append(f"  • {medium_count} MEDIUM severity")
    if low_count:
        summary_lines.append(f"  • {low_count} LOW severity")

    # Category breakdown
    if categories:
        summary_lines.append("Categories:")
        for cat, count in sorted(categories.items()):
            summary_lines.append(f"  • {cat}: {count}")

    # Detailed per-finding entries
    summary_lines.append("")
    summary_lines.append("Detailed findings:")
    for idx, f in enumerate(findings, start=1):
        file = f.get("file", "unknown")
        line = f.get("line")
        sev = f.get("severity", "MEDIUM")
        cat = f.get("category", "unknown")
        issue = f.get("issue", "(no description)")
        suggestion = f.get("suggestion", "(no suggestion)")

        if line is not None:
            loc = f"{file}:{line}"
        else:
            loc = file

        # Keep each finding to a few short lines
        summary_lines.append(f"{idx}. {loc} — {sev} ({cat})")
        summary_lines.append(f"   Issue: {issue}")
        summary_lines.append(f"   Suggestion: {suggestion}")

    summary = "\n".join(summary_lines)
    # Log compressed single-line version for visibility in logs
    logger.info(f"Summary: {summary.splitlines()[0]} | {len(findings)} findings")

    return {"final_summary": summary}
