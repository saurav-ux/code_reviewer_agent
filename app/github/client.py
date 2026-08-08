"""GitHub client wrapper for basic PR operations."""

from typing import Any, List, Dict
import os
import requests


class GitHubClient:
    def __init__(self, token: str | None = None, base_url: str | None = None) -> None:
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
        return f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"

    def get_pr(self, owner: str, repo: str, pr_number: int) -> Dict[str, Any]:
        url = self._url(f"repos/{owner}/{repo}/pulls/{pr_number}")
        resp = self.session.get(url)
        resp.raise_for_status()
        return resp.json()

    def get_changed_files(
        self, owner: str, repo: str, pr_number: int
    ) -> List[Dict[str, Any]]:
        files = []
        url = self._url(f"repos/{owner}/{repo}/pulls/{pr_number}/files")
        params = {"per_page": 100}
        while url:
            resp = self.session.get(url, params=params)
            resp.raise_for_status()
            page = resp.json()
            files.extend(page)
            # Handle pagination via Link header
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
        # Use the files API's 'patch' field which contains per-file diffs when available
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
