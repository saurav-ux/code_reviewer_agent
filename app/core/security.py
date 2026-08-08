"""Security helpers (placeholders)."""


def verify_signature(payload: bytes, signature: str) -> bool:
    """Verify request signature. Replace with real implementations."""
    # TODO: Implement HMAC verification against a webhook secret
    return True
