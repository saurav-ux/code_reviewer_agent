"""Preprocess node: clean and structure diff data."""

import logging
from typing import Dict, Any

from app.graph.state import ReviewState

logger = logging.getLogger("code_review_agent.preprocess")


def preprocess_diff(state: ReviewState) -> Dict[str, Any]:
    """Preprocess raw parsed diffs into structured format.
    
    Takes the parsed diffs from the webhook and cleans them:
    - Removes noise and empty entries
    - Extracts file names and added code content
    - Creates a clean structure for the reviewer
    
    Args:
        state: Current ReviewState containing parsed_diffs
    
    Returns:
        Updated state with processed_diffs
    """
    parsed_diffs = state.get("parsed_diffs", [])
    logger.info(f"Preprocessing {len(parsed_diffs)} diffs")
    
    processed = []
    
    for diff_entry in parsed_diffs:
        file_name = diff_entry.get("file", "unknown")
        diff_content = diff_entry.get("diff", "")
        
        if not diff_content or not diff_content.strip():
            logger.debug(f"Skipping empty diff for {file_name}")
            continue
        
        # Clean up the diff content: remove leading/trailing whitespace per line
        lines = diff_content.splitlines()
        cleaned_lines = [line.strip() for line in lines if line.strip()]
        cleaned_content = "\n".join(cleaned_lines)
        
        if cleaned_content:
            processed.append({
                "file": file_name,
                "content": cleaned_content,
                "original_diff": diff_content,
            })
            logger.debug(f"Processed {file_name}: {len(cleaned_lines)} lines")
    
    logger.info(f"Preprocessing complete. {len(processed)} diffs ready for review")
    
    return {
        "processed_diffs": processed,
    }
