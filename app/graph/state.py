"""Typed state for the code review graph."""

from typing import List, TypedDict


class ReviewState(TypedDict):
    """Shared state passed through the LangGraph code review pipeline."""
    
    owner: str
    repo: str
    pr_number: int
    parsed_diffs: List[dict]
    processed_diffs: List[dict]
    review_findings: List[dict]
    final_summary: str
    review_error: str | None
