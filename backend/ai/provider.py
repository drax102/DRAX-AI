"""
provider.py — Interface for future local or cloud LLM providers.
"""

from backend.core.logger import get_logger

logger = get_logger(__name__)


class LLMProvider:
    """Base interface for LLM extensions."""

    def generate_response(self, prompt: str) -> str:
        raise NotImplementedError
