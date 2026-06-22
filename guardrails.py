import re
from typing import List, Pattern

from config import Config


class GuardRailViolation(ValueError):
    pass


def _compile_blocked_patterns(blocked_keywords: List[str]) -> List[Pattern[str]]:
    patterns = []
    for phrase in blocked_keywords:
        normalized = phrase.strip()
        if not normalized:
            continue
        escaped = re.escape(normalized)
        patterns.append(re.compile(rf"\b{escaped}\b", re.IGNORECASE))
    return patterns


_BLOCKED_PROMPT_PATTERNS = _compile_blocked_patterns(Config.BLOCKED_PROMPT_KEYWORDS)


def enforce_prompt_guardrails(prompt: str) -> None:
    if not prompt or not prompt.strip():
        raise GuardRailViolation("Prompt cannot be empty.")

    if len(prompt) > Config.MAX_PROMPT_LENGTH:
        raise GuardRailViolation(
            f"Prompt exceeds maximum length of {Config.MAX_PROMPT_LENGTH} characters."
        )

    for pattern in _BLOCKED_PROMPT_PATTERNS:
        if pattern.search(prompt):
            raise GuardRailViolation(
                "Unsafe or disallowed content detected in the query. "
                "Please rephrase your request."
            )
