"""
backend/skills/web_skill.py — Universal web intelligence & information retrieval skill.
Handles weather, financial stocks, real-time news, and general knowledge.
"""

from typing import Optional, Dict, Any
from backend.skills.base import BaseSkill
from backend.tools.weather_tools import get_weather
from backend.tools.finance_tools import get_stock_price, fetch_quote
from backend.tools.news_tools import get_news
from backend.tools.knowledge_tools import get_knowledge
from backend.core.logger import get_logger

logger = get_logger(__name__)


class WebSkill(BaseSkill):
    name = "web_intelligence"
    category = "information"
    required_capability = "cloud"

    def _register_actions(self):
        self.register_action("weather", self.get_weather, "Get current weather conditions", "cloud")
        self.register_action("stock_quote", self.get_stock, "Fetch real-time stock quotes", "cloud")
        self.register_action("news", self.get_news, "Get latest news headlines", "cloud")
        self.register_action("knowledge", self.get_knowledge, "Search knowledge base or Wikipedia", "cloud")

    def get_weather(self, city: str = "Delhi") -> str:
        return get_weather(city)

    def get_stock(self, symbol: str = "NVDA") -> str:
        return get_stock_price(symbol)

    def get_news(self, topic: str = "world") -> str:
        return get_news(topic)

    def get_knowledge(self, query: str) -> str:
        return get_knowledge(query)


web_skill = WebSkill()
