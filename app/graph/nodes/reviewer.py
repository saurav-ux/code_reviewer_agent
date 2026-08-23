"""Reviewer node: invoke the code review agent."""

import logging
from typing import Dict, Any

from app.graph.state import ReviewState
from app.agents.code_reviewer import CodeReviewAgent

logger = logging.getLogger("code_review_agent.reviewer_node")


def review_code(state: ReviewState) -> Dict[str, Any]:
    """Review processed diffs using the CodeReviewAgent.
    
    Invokes the LLM-based code reviewer to analyze processed diffs
    and extract findings.
    
    Args:
        state: Current ReviewState containing processed_diffs
    
    Returns:
        Updated state with review_findings
    """
    processed_diffs = state.get("processed_diffs", [])
    logger.info(f"Starting code review for {len(processed_diffs)} diffs")
    
    try:
        agent = CodeReviewAgent()
        findings = agent.review(processed_diffs)
        logger.info(f"Code review complete. Found {len(findings)} issues")
        
        return {
            "review_findings": findings,
        }
    except Exception as e:
        logger.error(f"Code review failed: {e}")
        return {
            "review_findings": [],
        }
