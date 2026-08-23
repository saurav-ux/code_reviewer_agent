"""Code reviewer agent using Groq LLM."""

import json
import logging
from typing import List, Dict, Any

from langchain_groq import ChatGroq

from app.core.config import settings
from app.prompts.code_review import CODE_REVIEW_PROMPT

logger = logging.getLogger("code_review_agent.reviewer")


class CodeReviewAgent:
    """Agent that reviews code diffs using Groq LLM."""
    
    def __init__(self):
        """Initialize the code reviewer with Groq LLM."""
        if not settings.groq_api_key:
            raise ValueError("GROQ_API_KEY is not configured in environment")
        
        self.llm = ChatGroq(
            api_key=settings.groq_api_key,
            model=settings.groq_model,
            temperature=0,
        )
    
    def review(self, processed_diffs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Review code diffs and return structured findings.
        
        Args:
            processed_diffs: List of processed diff entries with file and content
        
        Returns:
            List of finding dictionaries with severity, category, issue, suggestion
        """
        if not processed_diffs:
            logger.info("No diffs to review")
            return []
        
        findings = []
        
        for diff_entry in processed_diffs:
            file_name = diff_entry.get("file", "unknown")
            content = diff_entry.get("content", "")
            
            if not content.strip():
                logger.debug(f"Skipping empty diff for {file_name}")
                continue
            
            logger.debug(f"Reviewing {file_name} ({len(content)} chars)")
            
            prompt = CODE_REVIEW_PROMPT.format(code_content=content)
            
            try:
                response = self.llm.invoke(prompt)
                response_text = response.content.strip()
                
                logger.debug(f"LLM response for {file_name}: {response_text[:200]}")
                
                parsed = self._parse_response(response_text, file_name)
                findings.extend(parsed)
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM response for {file_name}: {e}")
                continue
            except Exception as e:
                logger.error(f"Error reviewing {file_name}: {e}")
                continue
        
        logger.info(f"Review complete. Found {len(findings)} issues")
        return findings
    
    def _parse_response(self, response_text: str, file_name: str) -> List[Dict[str, Any]]:
        """Parse and validate LLM response.
        
        Args:
            response_text: Raw response from LLM
            file_name: Name of file being reviewed
        
        Returns:
            List of validated finding dictionaries
        """
        try:
            data = json.loads(response_text)
            findings = data.get("findings", [])
            
            validated = []
            for finding in findings:
                if self._validate_finding(finding):
                    # Always set the file to the source file being reviewed so the
                    # reported location comes from the actual diff, not the LLM.
                    finding["file"] = file_name
                    validated.append(finding)
            
            return validated
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in response: {e}")
            return []
    
    def _validate_finding(self, finding: Dict[str, Any]) -> bool:
        """Validate that a finding has required fields.
        
        Args:
            finding: Finding dictionary to validate
        
        Returns:
            True if valid, False otherwise
        """
        required = {"severity", "category", "issue", "suggestion"}
        if not all(k in finding for k in required):
            logger.warning(f"Incomplete finding: {finding}")
            return False
        
        if finding["severity"] not in {"HIGH", "MEDIUM", "LOW"}:
            logger.warning(f"Invalid severity: {finding['severity']}")
            return False
        
        if finding["category"] not in {"security", "bug", "quality", "performance", "best_practice"}:
            logger.warning(f"Invalid category: {finding['category']}")
            return False
        
        return True
