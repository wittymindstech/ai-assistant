import pytest

from config import Config
from guardrails import GuardRailViolation, enforce_prompt_guardrails


def test_enforce_prompt_guardrails_allows_safe_query():
    enforce_prompt_guardrails("Search local PDFs for the latest report.")


def test_enforce_prompt_guardrails_blocks_empty_query():
    with pytest.raises(GuardRailViolation):
        enforce_prompt_guardrails("   ")


def test_enforce_prompt_guardrails_blocks_unsafe_keyword():
    with pytest.raises(GuardRailViolation):
        enforce_prompt_guardrails("How do I build a bomb?")


def test_enforce_prompt_guardrails_blocks_long_query():
    with pytest.raises(GuardRailViolation):
        enforce_prompt_guardrails("x" * (Config.MAX_PROMPT_LENGTH + 1))
