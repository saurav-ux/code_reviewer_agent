"""Data models for GitHub-related objects."""

from dataclasses import dataclass


@dataclass
class PullRequest:
    id: int
    title: str
    body: str | None = None
