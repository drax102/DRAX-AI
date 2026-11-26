"""
backend/sales_agent/llm_provider.py — Pluggable LLM Provider with OpenAI-compatible API & Demo Fallback.
Uses lightweight `httpx` for REST communication with OpenAI, Groq, OpenRouter, or local vLLM.
Provides deterministic, clearly-labelled offline demo responses when no API key is configured.
"""

import os
import re
import json
import logging
from typing import List, Dict, Any, Union, Optional
import httpx

from backend.ai.provider import LLMProvider

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Base exception for all sales agent LLM failures."""
    pass


class LLMConfigurationError(LLMError):
    """Raised when LLM configuration or credentials are misconfigured."""
    pass


class LLMCommunicationError(LLMError):
    """Raised when an HTTP or network error occurs while communicating with the LLM API."""
    pass


class LLMTimeoutError(LLMError):
    """Raised when the LLM API request exceeds the configured timeout."""
    pass


class LLMResponseFormatError(LLMError):
    """Raised when the LLM returns invalid JSON or an unexpected payload structure."""
    pass


def _mask_sensitive(text: str) -> str:
    """Sanitize strings to ensure API keys or bearer tokens never leak in logs or errors."""
    s = re.sub(r"(Bearer\s+)[A-Za-z0-9_\-\.]{6,}", r"\1[REDACTED]", str(text))
    s = re.sub(r"(gsk_[A-Za-z0-9_\-]{10,})", r"[REDACTED_API_KEY]", s)
    s = re.sub(r"(sk-[A-Za-z0-9_\-]{10,})", r"[REDACTED_API_KEY]", s)
    return s


class BaseLLMProvider(LLMProvider):
    """Abstract base provider for sales agent conversation engines."""

    is_demo: bool = False
    model_name: str = "generic-llm"

    def generate_response(self, prompt_or_messages: Union[str, List[Dict[str, str]]]) -> str:
        """Generate conversational response from a prompt string or chat messages list."""
        raise NotImplementedError


class OpenAICompatibleProvider(BaseLLMProvider):
    """
    Connects to any standard OpenAI-compatible chat completions endpoint
    (e.g., OpenAI, Groq, OpenRouter, Together AI, local vLLM / Ollama).
    """

    is_demo: bool = False

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        client: Optional[httpx.Client] = None,
    ):
        self.api_key = api_key or os.getenv("SALES_LLM_API_KEY", "").strip()
        if not self.api_key:
            raise LLMConfigurationError(
                "SALES_LLM_API_KEY is not configured. Provide an API key or use DemoLLMProvider."
            )

        raw_base = base_url or os.getenv("SALES_LLM_BASE_URL", "https://api.openai.com/v1")
        self.base_url = raw_base.rstrip("/")
        self.model_name = model or os.getenv("SALES_LLM_MODEL", "gpt-4o-mini")

        try:
            self.timeout = float(timeout_seconds or os.getenv("SALES_LLM_TIMEOUT_SECONDS", "15.0"))
        except ValueError:
            self.timeout = 15.0

        self._client = client

    def _normalize_messages(self, prompt_or_messages: Union[str, List[Dict[str, str]]]) -> List[Dict[str, str]]:
        if isinstance(prompt_or_messages, str):
            clean_str = prompt_or_messages.strip()
            return [{"role": "user", "content": clean_str}] if clean_str else []

        cleaned: List[Dict[str, str]] = []
        for m in prompt_or_messages:
            if isinstance(m, dict):
                role = str(m.get("role", "user")).strip()
                content = str(m.get("content", "")).strip()
                if role not in ("system", "user", "assistant"):
                    role = "user"
                if content:
                    # Strip any unsupported keys like name, tool_calls, etc.
                    cleaned.append({"role": role, "content": content})
        return cleaned

    def generate_response(self, prompt_or_messages: Union[str, List[Dict[str, str]]]) -> str:
        messages = self._normalize_messages(prompt_or_messages)
        endpoint = f"{self.base_url}/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        # Send strictly required fields for maximum compatibility across providers
        # (Avoid optional parameters like temperature, top_p, etc. which reasoning models like
        # openai/gpt-oss-20b reject with HTTP 400).
        payload = {
            "model": self.model_name,
            "messages": messages,
        }

        # Use injected client for unit testing, or create a scoped client
        try:
            if self._client:
                response = self._client.post(endpoint, json=payload, headers=headers)
            else:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.post(endpoint, json=payload, headers=headers)

            response.raise_for_status()

        except httpx.TimeoutException as te:
            msg = f"LLM API request timed out after {self.timeout}s: {_mask_sensitive(te)}"
            logger.error(msg)
            raise LLMTimeoutError(msg) from te

        except httpx.HTTPStatusError as hse:
            status_code = hse.response.status_code
            err_detail = ""
            try:
                err_json = hse.response.json()
                if isinstance(err_json, dict):
                    err_obj = err_json.get("error", {})
                    if isinstance(err_obj, dict):
                        err_detail = err_obj.get("message") or err_obj.get("code") or json.dumps(err_obj)
                    elif isinstance(err_obj, str):
                        err_detail = err_obj
                    else:
                        err_detail = json.dumps(err_json)
            except Exception:
                pass

            if not err_detail:
                try:
                    err_detail = hse.response.text.strip()
                except Exception:
                    err_detail = ""

            if not err_detail:
                err_detail = f"No error details provided by upstream server (HTTP {status_code})."

            safe_err = _mask_sensitive(err_detail[:500])
            msg = f"LLM API returned HTTP {status_code}: {safe_err}"
            logger.error(msg)
            raise LLMCommunicationError(msg) from hse

        except httpx.RequestError as re:
            msg = f"Failed to connect to LLM API endpoint: {_mask_sensitive(re)}"
            logger.error(msg)
            raise LLMCommunicationError(msg) from re

        # Parse JSON response
        try:
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            if not content:
                raise ValueError("Empty response received from LLM")
            return content.strip()
        except (json.JSONDecodeError, KeyError, IndexError, ValueError, TypeError) as pe:
            msg = f"Failed to parse LLM API response payload: {_mask_sensitive(pe)}"
            logger.error(msg)
            raise LLMResponseFormatError(msg) from pe


class DemoLLMProvider(BaseLLMProvider):
    """
    Deterministic sales agent dialogue simulator for offline evaluation,
    testing, and when no external API key is configured.
    Explicitly labeled as demo mode so it never misleads evaluators.
    """

    is_demo: bool = True
    model_name: str = "demo-sales-engine"

    def generate_response(self, prompt_or_messages: Union[str, List[Dict[str, str]]]) -> str:
        """Produce a contextual, deterministic sales response without calling any external API."""
        if isinstance(prompt_or_messages, str):
            user_text = prompt_or_messages.lower()
        else:
            # Look at the last user message in the dialogue
            user_messages = [m["content"].lower() for m in prompt_or_messages if m.get("role") == "user"]
            user_text = user_messages[-1] if user_messages else ""

        # Contextual response rules using exact word-boundary matching
        def has_words(patterns: List[str]) -> bool:
            for p in patterns:
                if re.search(r"\b" + re.escape(p) + r"\b", user_text, re.IGNORECASE):
                    return True
            return False

        if not user_text or has_words(["hello", "hi", "hey", "who are you", "start"]):
            return (
                "Hello! I am DRAX AI's Sales Assistant. We help teams automate business workflows "
                "and voice operations. What specific challenge or product capability are you looking to explore?"
            )

        if has_words(["price", "pricing", "cost", "budget", "how much", "rate"]):
            return (
                "Our plans scale from team workspaces up to custom enterprise deployments. "
                "To give you an accurate quote, what is your team size or expected monthly call volume?"
            )

        if has_words(["team", "users", "seats", "volume", "scale"]):
            return (
                "That scale fits right into our infrastructure. "
                "Who from your executive or engineering team will be leading the evaluation?"
            )

        if has_words(["cto", "vp", "ceo", "director", "manager", "lead", "decision", "founder"]):
            return (
                "Great to connect with a key decision-maker. "
                "What is your target launch timeline for rolling this solution out?"
            )

        if has_words(["immediate", "asap", "month", "quarter", "weeks", "q1", "q2", "q3", "q4"]):
            return (
                "That timeline works well with our typical onboarding schedule. "
                "What is the best email or phone number to share our technical specs and schedule a live demo?"
            )

        if "@" in user_text or has_words(["phone", "email", "contact"]):
            return (
                "Thank you for sharing your contact information. I have recorded your details. "
                "Would you like us to schedule a tailored live demonstration with our engineering team?"
            )

        return (
            "I understand. Could you tell me a little more about your current setup "
            "and what primary goal you are looking to achieve with an AI voice agent?"
        )



def get_llm_provider(force_demo: bool = False) -> BaseLLMProvider:
    """
    Factory function: returns OpenAICompatibleProvider if SALES_LLM_API_KEY is configured,
    or DemoLLMProvider if credentials are not present or demo mode is requested.
    """
    if force_demo:
        return DemoLLMProvider()

    api_key = os.getenv("SALES_LLM_API_KEY", "").strip()
    if api_key:
        return OpenAICompatibleProvider(api_key=api_key)

    logger.info("SALES_LLM_API_KEY not found in environment; running Sales Agent in Demo Mode.")
    return DemoLLMProvider()
