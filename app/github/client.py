"""GitHub client wrapper for basic PR operations."""

from typing import Any, Dict, List
import os
import logging

import requests

logger = logging.getLogger("code_review_agent.github_client")


class GitHubClient:
    """Client for interacting with the GitHub pull request API.

    This wrapper provides basic operations for retrieving pull request
    metadata, changed files, and per-file diffs.

    Args:
        token: GitHub authentication token. If not provided, the
            ``GITHUB_TOKEN`` environment variable is used.
        base_url: Base URL for the GitHub API. If not provided, the
            ``GITHUB_API`` environment variable is used, defaulting to
            ``https://api.github.com``.
    """

    def __init__(self, token: str | None = None, base_url: str | None = None) -> None:
        """Initialize the GitHub client."""
        token_value = token or os.getenv("GITHUB_TOKEN")
        self.token = token_value.strip() if isinstance(token_value, str) else None
        self.base_url = (
            base_url or os.getenv("GITHUB_API", "https://api.github.com")
        ).strip()
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "code-review-agent",
            }
        )
        if self.token:
            self.session.headers.update({"Authorization": f"token {self.token}"})

    def _url(self, path: str) -> str:
        """Build a complete GitHub API URL.

        Args:
            path: API path to append to the configured base URL.

        Returns:
            The complete API URL.
        """
        return f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"

    def get_pr(self, owner: str, repo: str, pr_number: int) -> Dict[str, Any]:
        """Retrieve pull request metadata.

        Args:
            owner: GitHub repository owner or organization.
            repo: GitHub repository name.
            pr_number: Pull request number.

        Returns:
            A dictionary containing the pull request metadata.

        Raises:
            requests.HTTPError: If the GitHub API request fails.
        """
        url = self._url(f"repos/{owner}/{repo}/pulls/{pr_number}")
        resp = self.session.get(url)
        resp.raise_for_status()
        return resp.json()

    def get_changed_files(
        self, owner: str, repo: str, pr_number: int
    ) -> List[Dict[str, Any]]:
        """Retrieve all files changed by a pull request.

        The GitHub API is paginated, so this method follows ``Link`` headers
        until all available pages have been retrieved.

        Args:
            owner: GitHub repository owner or organization.
            repo: GitHub repository name.
            pr_number: Pull request number.

        Returns:
            A list of dictionaries describing the files changed by the
            pull request.

        Raises:
            requests.HTTPError: If any GitHub API request fails.
        """
        files = []
        url = self._url(f"repos/{owner}/{repo}/pulls/{pr_number}/files")
        params = {"per_page": 100}
        while url:
            resp = self.session.get(url, params=params)
            resp.raise_for_status()
            page = resp.json()
            files.extend(page)

            # Handle pagination via Link header.
            link = resp.headers.get("Link")
            next_url = None
            if link:
                parts = link.split(",")
                for part in parts:
                    if 'rel="next"' in part:
                        next_url = part.split(";")[0].strip().strip("<>")
            url = next_url
            params = {}

        return files

    def get_diff(self, owner: str, repo: str, pr_number: int) -> List[Dict[str, Any]]:
        """Retrieve per-file diffs for a pull request.

        The GitHub files API provides the patch for each changed file when
        available.

        Args:
            owner: GitHub repository owner or organization.
            repo: GitHub repository name.
            pr_number: Pull request number.

        Returns:
            A list of dictionaries containing the filename, status, and patch
            for each changed file.
        """
        files = self.get_changed_files(owner, repo, pr_number)
        result = []
        for f in files:
            result.append(
                {
                    "filename": f.get("filename"),
                    "status": f.get("status"),
                    "patch": f.get("patch") or "",
                }
            )
        return result

    # Issue comments helpers
    def get_issue_comments(self, owner: str, repo: str, issue_number: int) -> List[Dict[str, Any]]:
        """Retrieve comments for an issue or PR.

        Args:
            owner: Repository owner
            repo: Repository name
            issue_number: Issue or PR number

        Returns:
            List of comment objects
        """
        url = self._url(f"repos/{owner}/{repo}/issues/{issue_number}/comments")
        resp = self.session.get(url, params={"per_page": 100})
        resp.raise_for_status()
        return resp.json()

    def create_issue_comment(self, owner: str, repo: str, issue_number: int, body: str) -> Dict[str, Any]:
        """Create a comment on an issue or PR."""
        url = self._url(f"repos/{owner}/{repo}/issues/{issue_number}/comments")
        resp = self.session.post(url, json={"body": body})
        if resp.status_code >= 400:
            # Log response body to aid debugging (do not log entire token)
            logger.error("GitHub create comment failed: %s %s", resp.status_code, resp.text)
        resp.raise_for_status()
        return resp.json()

    def update_issue_comment(self, owner: str, repo: str, comment_id: int, body: str) -> Dict[str, Any]:
        """Update an existing issue comment by ID."""
        url = self._url(f"repos/{owner}/{repo}/issues/comments/{comment_id}")
        resp = self.session.patch(url, json={"body": body})
        if resp.status_code >= 400:
            logger.error("GitHub update comment failed: %s %s", resp.status_code, resp.text)
        resp.raise_for_status()
        return resp.json()

    # High-level helper that creates or updates a single bot comment per PR
    BOT_MARKER = "<!-- code-review-agent-comment -->"

    def create_or_update_pr_comment(self, owner: str, repo: str, pr_number: int, body: str) -> Dict[str, Any]:
        """Create or update a bot comment on a PR. Uses a hidden marker to
        find existing bot comments and update them instead of creating new
        ones on every run.

        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: PR number
            body: Comment body (should include BOT_MARKER)

        Returns:
            The created or updated comment object
        """
        # Ensure marker is present
        if self.BOT_MARKER not in body:
            body = f"{self.BOT_MARKER}\n\n{body}"

        comments = self.get_issue_comments(owner, repo, pr_number)
        for c in comments:
            cbody = c.get("body") or ""
            if self.BOT_MARKER in cbody and c.get("user", {}).get("type") in ("Bot", "User"):
                # Update existing
                return self.update_issue_comment(owner, repo, c["id"], body)

        # Not found -> create
        return self.create_issue_comment(owner, repo, pr_number, body)
