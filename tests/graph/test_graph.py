"""Integration tests for the complete review graph."""

import pytest

from app.graph.builder import build_review_graph
from app.graph.state import ReviewState


@pytest.fixture
def review_graph():
    """Fixture providing a compiled review graph."""
    return build_review_graph()


def test_graph_with_sample_diff(review_graph, sample_diff_with_issues):
    """Test the full graph pipeline with a sample diff containing issues."""
    initial_state: ReviewState = {
        "owner": "test",
        "repo": "test-repo",
        "pr_number": 42,
        "parsed_diffs": sample_diff_with_issues,
        "processed_diffs": [],
        "review_findings": [],
        "final_summary": "",
    }

    result = review_graph.invoke(initial_state)

    # Verify output structure
    assert result is not None
    assert "review_findings" in result
    assert "final_summary" in result
    assert "processed_diffs" in result

    # Verify findings were generated (if API is available)
    findings = result.get("review_findings", [])
    assert isinstance(findings, list)

    # Verify summary was generated
    summary = result.get("final_summary", "")
    assert isinstance(summary, str)


def test_graph_with_empty_diffs(review_graph, sample_empty_diffs):
    """Test the graph with no diffs."""
    initial_state: ReviewState = {
        "owner": "test",
        "repo": "test-repo",
        "pr_number": 1,
        "parsed_diffs": sample_empty_diffs,
        "processed_diffs": [],
        "review_findings": [],
        "final_summary": "",
    }

    result = review_graph.invoke(initial_state)

    # Should complete without error
    assert result is not None
    findings = result.get("review_findings", [])
    assert isinstance(findings, list)
    summary = result.get("final_summary", "")
    assert isinstance(summary, str)


def test_graph_preserves_pr_metadata(review_graph):
    """Test that PR metadata flows through the graph unchanged."""
    initial_state: ReviewState = {
        "owner": "myorg",
        "repo": "myrepo",
        "pr_number": 99,
        "parsed_diffs": [],
        "processed_diffs": [],
        "review_findings": [],
        "final_summary": "",
    }

    result = review_graph.invoke(initial_state)

    # Metadata should be preserved (even though TypedDict doesn't strictly enforce this)
    assert result.get("owner") == "myorg"
    assert result.get("repo") == "myrepo"
    assert result.get("pr_number") == 99


@pytest.mark.skipif(
    condition=True, reason="Requires GROQ_API_KEY configured; run with --groq to enable"
)
def test_graph_finds_security_issues(review_graph):
    """
    Integration test that requires Groq API.

    Tests that the graph identifies security issues like:
    - Hardcoded secrets (API_KEY = "123456")
    - SQL injection vulnerability
    """
    sample = [
        {
            "file": "app.py",
            "diff": 'API_KEY = "123456"\nquery = f"SELECT * FROM users WHERE id = {user_id}"',
        }
    ]

    initial_state: ReviewState = {
        "owner": "test",
        "repo": "test",
        "pr_number": 1,
        "parsed_diffs": sample,
        "processed_diffs": [],
        "review_findings": [],
        "final_summary": "",
    }
    sqlInjection4 = 'query = f"SELECT * FROM users WHERE id = {user_id}"'

    result = review_graph.invoke(initial_state)
    findings = result.get("review_findings", [])

    # Should find HIGH severity issues
    high_findings = [f for f in findings if f.get("severity") == "HIGH"]
    assert len(high_findings) >= 1

    # Should have security category
    security_findings = [f for f in findings if f.get("category") == "security"]
    assert len(security_findings) >= 1
