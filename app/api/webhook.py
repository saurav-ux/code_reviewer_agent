"""GitHub webhook endpoints and helpers."""

import hmac
import hashlib
from typing import Any, Dict
import json
import logging

import requests

from fastapi import APIRouter, Header, HTTPException, Request
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_401_UNAUTHORIZED

from app.core.config import settings
from app.github.client import GitHubClient
from app.services.diff_parser import parse_diff
from app.graph.builder import get_review_graph
from app.graph.state import ReviewState
from app.schemas.review import ReviewResponse, ReviewFinding

logger = logging.getLogger("code_review_agent.webhook")

router = APIRouter()


def verify_signature(secret: str, body: bytes, signature_header: str | None) -> bool:
    """Verify a GitHub webhook signature.

    GitHub signs webhook payloads using HMAC-SHA256. This function computes
    the expected signature using the configured secret and compares it with
    the signature supplied in the ``X-Hub-Signature-256`` header.

    Args:
        secret: Secret configured for the GitHub webhook.
        body: Raw webhook request body.
        signature_header: Value of the ``X-Hub-Signature-256`` header.

    Returns:
        True if the signature is valid; otherwise, False.
    """
    if not signature_header:
        return False
    try:
        sha_name, signature = signature_header.split("=", 1)
    except ValueError:
        return False
    if sha_name != "sha256":
        return False
    mac = hmac.new(secret.encode(), msg=body, digestmod=hashlib.sha256)
    expected = mac.hexdigest()
    return hmac.compare_digest(expected, signature)


@router.post("/webhook")
async def github_webhook(
    request: Request,
    x_hub_signature_256: str | None = Header(None),
    x_github_event: str | None = Header(None),
) -> Dict[str, Any]:
    """Handle incoming GitHub webhook events.

    The endpoint validates the webhook signature, handles GitHub ping events,
    ignores unsupported event types, and processes pull request events by
    fetching and parsing the changed files.

    Args:
        request: Incoming FastAPI request containing the GitHub webhook
            payload.
        x_hub_signature_256: GitHub HMAC-SHA256 signature for the request body.
        x_github_event: GitHub event type provided in the request header.

    Returns:
        A dictionary containing the webhook processing status. Ping events
        return a ``pong`` response, unsupported events are marked as ignored,
        and pull request events return parsed diffs.

    Raises:
        HTTPException: If the webhook secret is not configured, the signature
            is invalid, required repository or pull request information is
            missing, or the GitHub API request fails.
    """
    body = await request.body()

    logger.info(
        "Incoming GitHub webhook request — event=%s has_signature=%s",
        x_github_event,
        x_hub_signature_256 is not None,
    )
    print(
        "Incoming GitHub webhook request — event=%s has_signature=%s"
        % (x_github_event, x_hub_signature_256 is not None)
    )

    secret = settings.github_webhook_secret
    if secret:
        secret = secret.strip()

    if not secret:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST, detail="Webhook secret not configured"
        )

    if not verify_signature(secret, body, x_hub_signature_256):
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED, detail="Invalid signature"
        )

    payload = await request.json()

    logger.info("GitHub event: %s", x_github_event)

    if x_github_event == "ping":
        return {"status": "pong"}

    if x_github_event != "pull_request":
        return {
            "status": "ignored",
            "event": x_github_event,
            "action": payload.get("action"),
        }

    # Basic extraction for pull request events
    action = payload.get("action")
    pr = payload.get("pull_request") or {}
    pr_number = pr.get("number")

    repository = payload.get("repository") or {}
    owner = repository.get("owner", {}).get("login")
    repo = repository.get("name")

    if not owner or not repo:
        base_repo = pr.get("base", {}).get("repo") or {}
        owner = owner or base_repo.get("owner", {}).get("login")
        repo = repo or base_repo.get("name")

    logger.info(
        "Webhook received — action=%s owner=%s repo=%s pr=%s",
        action,
        owner,
        repo,
        pr_number,
    )

    if not all([owner, repo, pr_number]):
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail="Missing repository or PR information",
        )

    # Initialize GitHub client
    gh = GitHubClient(token=settings.github_token, base_url=settings.github_api)

    logger.info("Fetching changed files for %s/%s PR #%s", owner, repo, pr_number)
    try:
        files = gh.get_changed_files(owner, repo, pr_number)
    except requests.HTTPError as exc:
        response = exc.response
        status_code = response.status_code if response is not None else None
        body_text = None
        if response is not None:
            body_text = response.text.strip()
            if len(body_text) > 500:
                body_text = body_text[:500] + "..."
        logger.error("GitHub API error: %s %s", status_code, exc)
        if body_text:
            logger.debug("GitHub response: %s", body_text)

        if status_code == 404:
            detail = (
                "Resource not found or inaccessible. "
                "Verify the repository owner/name, PR number, and token permissions."
            )
        elif status_code == 403:
            detail = (
                "Access forbidden. Ensure the GitHub token has the required repo scopes "
                "and can access this repository."
            )
        elif status_code == 401:
            detail = "Authentication failed. Verify the GitHub token is valid."
        else:
            detail = f"GitHub API error fetching changed files: {exc}"

        raise HTTPException(status_code=status_code or 502, detail=detail)

    for f in files:
        logger.info("  %s", f.get("filename"))

    logger.info("Parsing diffs from file entries")
    structured = []
    for item in files:
        parsed = parse_diff(item.get("patch", ""))
        parsed["file"] = item.get("filename")
        structured.append(parsed)

    logger.info("Done. Parsed %d diffs.", len(structured))
    logger.debug("Parsed diffs:\n%s", json.dumps(structured, indent=2))

    # Invoke the LangGraph review pipeline
    logger.info("Invoking code review graph")
    try:
        graph = get_review_graph()
        
        initial_state: ReviewState = {
            "owner": owner,
            "repo": repo,
            "pr_number": pr_number,
            "parsed_diffs": structured,
            "processed_diffs": [],
            "review_findings": [],
            "final_summary": "",
        }
        
        result = graph.invoke(initial_state)
        
        findings_data = result.get("review_findings", [])
        summary = result.get("final_summary", "")
        
        logger.info(f"Graph execution complete. Findings: {len(findings_data)}, Summary: {summary[:50]}...")
        
        # Convert findings to ReviewFinding objects
        findings = []
        for finding in findings_data:
            try:
                rf = ReviewFinding(
                    file=finding.get("file", "unknown"),
                    line=finding.get("line"),
                    severity=finding.get("severity", "MEDIUM"),
                    category=finding.get("category", "quality"),
                    issue=finding.get("issue", ""),
                    suggestion=finding.get("suggestion", ""),
                )
                findings.append(rf)
            except Exception as e:
                logger.error(f"Failed to create ReviewFinding: {e}")
                continue
        
        response = ReviewResponse(
            status="review_completed",
            pr_number=pr_number,
            findings=findings,
            summary=summary,
        )
        
        logger.info(f"Webhook response: {response.status}, {len(findings)} findings")

        # Post findings as a PR comment (create or update a single bot comment)
        try:
            from app.utils.markdown import render_findings_markdown

            markdown = render_findings_markdown(response.model_dump())
            gh.create_or_update_pr_comment(owner, repo, pr_number, markdown)
            logger.info("Posted code review comment to %s/%s#%s", owner, repo, pr_number)
        except Exception as exc:
            logger.error("Failed to post PR comment: %s", exc, exc_info=True)

        return response.model_dump()
        
    except Exception as e:
        logger.error(f"Code review graph execution failed: {e}", exc_info=True)
        response = ReviewResponse(
            status="review_failed",
            pr_number=pr_number,
            findings=[],
            summary=f"Code review failed: {str(e)}",
        )
        return response.model_dump()
