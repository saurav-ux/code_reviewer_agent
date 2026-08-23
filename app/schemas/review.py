"""Schema definitions for code review findings."""

from typing import List
from pydantic import BaseModel, Field


class ReviewFinding(BaseModel):
    """A single code review finding."""
    
    file: str = Field(..., description="File path where issue was found")
    line: int | None = Field(None, description="Line number (if applicable)")
    severity: str = Field(..., description="Severity level: HIGH, MEDIUM, LOW")
    category: str = Field(..., description="Category: security, bug, quality, performance, best_practice")
    issue: str = Field(..., description="Brief description of the issue")
    suggestion: str = Field(..., description="Suggested fix or improvement")


class ReviewResponse(BaseModel):
    """Response from a code review."""
    
    status: str = Field(default="review_completed", description="Status of review")
    pr_number: int = Field(..., description="Pull request number")
    findings: List[ReviewFinding] = Field(default_factory=list, description="List of review findings")
    summary: str = Field(default="", description="Summary of the review")
