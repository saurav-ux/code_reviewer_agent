"""Fixtures for code review tests."""

import pytest


# Sample diffs for testing
SAMPLE_DIFF_WITH_SECRETS = """
def get_user(user_id):
    API_KEY = "123456"
    conn = db.connect()
    query = f"SELECT * FROM users WHERE id = {user_id}"
    return conn.execute(query).fetchone()
"""

SAMPLE_DIFF_CLEAN = """
def calculate_sum(a, b):
    return a + b
"""

SAMPLE_PARSED_DIFFS = [
    {
        "file": "app/api/users.py",
        "diff": SAMPLE_DIFF_WITH_SECRETS.strip(),
    }
]

SAMPLE_EMPTY_DIFFS = []


@pytest.fixture
def sample_diff_with_issues():
    """Fixture providing a diff with security and quality issues."""
    return SAMPLE_PARSED_DIFFS


@pytest.fixture
def sample_clean_diff():
    """Fixture providing a clean diff."""
    return [
        {
            "file": "app/utils/math.py",
            "diff": SAMPLE_DIFF_CLEAN.strip(),
        }
    ]


@pytest.fixture
def sample_empty_diffs():
    """Fixture providing empty diffs."""
    return SAMPLE_EMPTY_DIFFS
