"""GitHub webhook endpoints and helpers."""

import hmac
import hashlib
import os
from typing import Dict, Any

from fastapi import APIRouter, Header, HTTPException, Request
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_401_UNAUTHORIZED

from app.core.config import settings
from app.github.client import GitHubClient
from app.services.diff_parser import parse_diff

router = APIRouter()


def verify_signature(secret: str, body: bytes, signature_header: str | None) -> bool:
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
    body = await request.body()

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

    print("GitHub event:", x_github_event)

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

    print("Webhook received")
    print()
    print("Repository:")
    print(repo)
    print()
    print("PR:")
    print(f"#{pr_number}")

    if not all([owner, repo, pr_number]):
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail="Missing repository or PR information",
        )

    # Initialize GitHub client
    gh = GitHubClient(token=settings.github_token, base_url=settings.github_api)

    print()
    print("Files Changed by me:")
    files = gh.get_changed_files(owner, repo, pr_number)
    for f in files:
        print(f.get("filename"))

    print()
    print("Fetching diff...")
    diffs = gh.get_diff(owner, repo, pr_number)
    structured = []
    for item in diffs:
        parsed = parse_diff(item.get("patch", ""))
        parsed["file"] = item.get("filename")
        structured.append(parsed)

    print()
    print("Done.")

    # Log output summary
    print("----------------")
    print("Diffs parsed:")
    for s in structured:
        print(s)

    return {"status": "ok", "diffs": structured}
