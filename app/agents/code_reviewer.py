"""Code reviewer agent using Groq LLM."""

import json
import logging
from typing import List, Dict, Any

from langchain_groq import ChatGroq

from app.core.config import settings
from app.prompts.code_review import CODE_REVIEW_PROMPT

logger = logging.getLogger("code_review_agent.reviewer")


class ReviewResponseError(ValueError):
    """Raised when the LLM response cannot satisfy the review contract."""


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
            
            parsed = None
            for attempt in range(2):
                try:
                    retry_note = ""
                    if attempt:
                        retry_note = (
                            "\nYour previous response was invalid or truncated. "
                            "Return compact, complete JSON only."
                        )
                    response = self.llm.invoke(prompt + retry_note)
                    response_text = response.content.strip()

                    logger.debug(
                        "LLM response for %s (attempt %d): %s",
                        file_name,
                        attempt + 1,
                        response_text[:200],
                    )
                    parsed = self._parse_response(response_text, file_name)
                    break
                except (json.JSONDecodeError, ReviewResponseError) as exc:
                    logger.warning(
                        "Invalid LLM response for %s on attempt %d: %s",
                        file_name,
                        attempt + 1,
                        exc,
                    )
                    if attempt == 1:
                        raise ReviewResponseError(
                            f"LLM returned invalid JSON for {file_name}"
                        ) from exc
                except Exception:
                    logger.exception("Error reviewing %s", file_name)
                    raise

            findings.extend(parsed or [])
        
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
        data = json.loads(response_text)
        if not isinstance(data, dict) or not isinstance(data.get("findings"), list):
            raise ReviewResponseError("Response must contain a findings array")

        findings = data["findings"]
        validated = []
        for finding in findings:
            if not isinstance(finding, dict) or not self._validate_finding(finding):
                raise ReviewResponseError("Response contains an invalid finding")
            # Always set the file to the source file being reviewed so the
            # reported location comes from the actual diff, not the LLM.
            finding["file"] = file_name
            validated.append(finding)

        return validated
    
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
