"""
knowledge_tools.py — Direct Wikipedia and general knowledge query tools.
Provides instant answers for "Who is...", "What is...", "Tell me about...", etc.
"""

import wikipedia
import webbrowser
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
    for prefix in ["who is the ", "who is ", "what is the ", "what is ", "what was ", "who was ", "tell me about ", "can you tell me about "]:
        if clean.lower().startswith(prefix):
            clean = clean[len(prefix):].strip()
    clean = clean.replace("?", "").strip()

    if not clean:
        return "What would you like to know about?"

    try:
        # Set user agent and language
        wikipedia.set_lang("en")
        summary = wikipedia.summary(clean, sentences=2, auto_suggest=True)
        logger.info(f"Retrieved Wikipedia summary for '{clean}'")
        return summary
    except Exception as e:
        logger.warning(f"Wikipedia lookup failed for '{clean}': {e} — falling back to Google search")
        url = f"https://www.google.com/search?q={clean}"
        webbrowser.open(url)
        return f"Searching Google for {clean}."
