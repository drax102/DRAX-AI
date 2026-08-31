"""
knowledge_tools.py — Direct Wikipedia and general knowledge query tools.
Provides instant answers for "Who is...", "What is...", "Tell me about...", etc.
Resilient on both Cloud and Local environments with lazy imports and REST API fallback.
"""

import sys
import urllib.parse
import requests

from backend.agent.tool_registry import register_tool
from backend.core.logger import get_logger

logger = get_logger(__name__)


@register_tool(
    name="get_knowledge",
    description="Get factual information, definitions, or summaries about people, places, history, science, or concepts.",
    parameters={
        "query": {"type": "string", "description": "Subject or question to look up (e.g. 'Prime Minister of India', 'Elon Musk', 'Black hole')"}
    },
    risk_level="low",
    category="knowledge",
)
def get_knowledge(query: str) -> str:
    clean = query.strip()
    for prefix in [
        "who is the ", "who is ", "what is the ", "what is ", "what was ",
        "who was ", "tell me about ", "can you tell me about ", "tell me "
    ]:
        if clean.lower().startswith(prefix):
            clean = clean[len(prefix):].strip()
    clean = clean.replace("?", "").strip()

    if not clean:
        return "What would you like to know about?"

    # Method 1: Try Python wikipedia library if available (lazy import)
    try:
        import wikipedia
        wikipedia.set_lang("en")
        summary = wikipedia.summary(clean, sentences=2, auto_suggest=True)
        if summary and summary.strip():
            logger.info(f"Retrieved Wikipedia summary for '{clean}' via wikipedia library")
            return summary.strip()
    except Exception as e:
        logger.info(f"Wikipedia library lookup for '{clean}' returned: {e} — trying REST fallback")

    # Method 2: Wikipedia Public REST API fallback (Zero dependency, fast & cloud-safe)
    try:
        encoded = urllib.parse.quote(clean.replace(" ", "_"))
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{encoded}"
        headers = {"User-Agent": "DRAX-AI/2.0 (personal-assistant; contact@drax.ai)"}
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            extract = data.get("extract", "")
            if extract and extract.strip():
                logger.info(f"Retrieved Wikipedia summary for '{clean}' via REST API")
                return extract.strip()
    except Exception as e:
        logger.warning(f"Wikipedia REST API fallback failed for '{clean}': {e}")

    # Method 3: Clean informative response
    if sys.platform == "win32":
        try:
            import webbrowser
            webbrowser.open(f"https://www.google.com/search?q={urllib.parse.quote(clean)}")
            return f"Searching Google for {clean}."
        except Exception:
            pass

    return f"I could not find a verified encyclopedia entry for '{clean}'. Try asking with more specific keywords."
