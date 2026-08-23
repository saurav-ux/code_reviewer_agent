"""Tests for the preprocess node."""

from app.graph.nodes.preprocess import preprocess_diff


def test_preprocess_with_diffs(sample_diff_with_issues):
    """Test that preprocess correctly cleans and structures diffs."""
    state = {
        "owner": "test",
        "repo": "test-repo",
        "pr_number": 1,
        "parsed_diffs": sample_diff_with_issues,
        "processed_diffs": [],
        "review_findings": [],
        "final_summary": "",
    }
    
    result = preprocess_diff(state)
    
    processed = result.get("processed_diffs", [])
    assert len(processed) > 0
    assert "file" in processed[0]
    assert "content" in processed[0]
    assert processed[0]["file"] == "app/api/users.py"
    assert "API_KEY" in processed[0]["content"]


def test_preprocess_with_empty_diffs(sample_empty_diffs):
    """Test that preprocess handles empty diff list."""
    state = {
        "owner": "test",
        "repo": "test-repo",
        "pr_number": 1,
        "parsed_diffs": sample_empty_diffs,
        "processed_diffs": [],
        "review_findings": [],
        "final_summary": "",
    }
    
    result = preprocess_diff(state)
    
    processed = result.get("processed_diffs", [])
    assert len(processed) == 0


def test_preprocess_strips_whitespace(sample_clean_diff):
    """Test that preprocess strips extra whitespace."""
    diffs = [
        {
            "file": "test.py",
            "diff": "  line1  \n  line2  \n  line3  ",
        }
    ]
    
    state = {
        "owner": "test",
        "repo": "test-repo",
        "pr_number": 1,
        "parsed_diffs": diffs,
        "processed_diffs": [],
        "review_findings": [],
        "final_summary": "",
    }
    
    result = preprocess_diff(state)
    
    processed = result.get("processed_diffs", [])
    assert len(processed) == 1
    # Check that content has been cleaned
    assert "line1" in processed[0]["content"]
    lines = processed[0]["content"].splitlines()
    # Lines should be stripped
    for line in lines:
        assert line == line.strip()
