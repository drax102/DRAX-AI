"""
news_tools.py — Global, Regional, Topic, and AI news tools using public RSS feeds.
Provides structured news with sources and timestamps without requiring paid API keys.
"""

import datetime
import urllib.parse
import feedparser

from backend.agent.tool_registry import register_tool
from backend.database.db import get_tasks, get_active_reminders, get_watchlist
from backend.core.logger import get_logger

logger = get_logger(__name__)

RSS_FEEDS = {
    "world": "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en",
    "india": "https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en",
    "technology": "https://news.google.com/rss/headlines/section/topic/TECHNOLOGY?hl=en-US&gl=US&ceid=US:en",
    "business": "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=en-US&gl=US&ceid=US:en",
    "ai": "https://news.google.com/rss/search?q=Artificial+Intelligence&hl=en-US&gl=US&ceid=US:en",
}


def fetch_rss_news(feed_url: str, limit: int = 5) -> list[dict]:
    """Parse RSS feed into structured article records."""
    articles = []
    try:
        feed = feedparser.parse(feed_url)
        for entry in feed.entries[:limit]:
            title = entry.get("title", "")
            source = entry.get("source", {}).get("title", "News") if "source" in entry else "News"
            published = entry.get("published", "")
            link = entry.get("link", "")
            articles.append({
                "title": title,
                "source": source,
                "published": published,
                "link": link,
            })
    except Exception as e:
        logger.error(f"Failed to fetch RSS feed {feed_url}: {e}")
    return articles


@register_tool(
    name="get_news",
    description="Get the latest news headlines by topic (AI, tech, business, world) or region (India, Punjab, Delhi).",
    parameters={
        "topic_or_region": {"type": "string", "description": "Topic (AI, tech, world) or region/city (India, Punjab, US)", "default": "world"},
        "limit": {"type": "integer", "description": "Number of articles", "default": 4},
    },
    risk_level="low",
    category="news",
)
def get_news(topic_or_region: str = "world", limit: int = 4) -> str:
    query = topic_or_region.lower().strip()

    if query in ["india", "indian", "delhi", "punjab", "mumbai"]:
        if query in ["delhi", "punjab", "mumbai"]:
            feed_url = f"https://news.google.com/rss/search?q={urllib.parse.quote(query)}+news&hl=en-IN&gl=IN&ceid=IN:en"
        else:
            feed_url = RSS_FEEDS["india"]
    elif "ai" in query or "artificial intelligence" in query:
        feed_url = RSS_FEEDS["ai"]
    elif "tech" in query or "technology" in query:
        feed_url = RSS_FEEDS["technology"]
    elif "business" in query or "market" in query or "finance" in query:
        feed_url = RSS_FEEDS["business"]
    elif query not in ["world", "global", "news"]:
        feed_url = f"https://news.google.com/rss/search?q={urllib.parse.quote(query)}&hl=en-US&gl=US&ceid=US:en"
    else:
        feed_url = RSS_FEEDS["world"]

    articles = fetch_rss_news(feed_url, limit=limit)
    if not articles:
        return f"Could not retrieve news for '{topic_or_region}' right now."

    lines = [f"- {a['title']}" for a in articles]
    header = f"Top {topic_or_region.title()} News Headlines:"
    return f"{header}\n" + "\n".join(lines)


@register_tool(
    name="get_daily_briefing",
    description="Generate a complete morning/daily briefing covering date, weather, tasks, reminders, and top news.",
    parameters={"city": {"type": "string", "description": "City for weather", "default": "Delhi"}},
    risk_level="low",
    category="news",
)
def get_daily_briefing(city: str = "Delhi") -> str:
    now = datetime.datetime.now()
    date_str = now.strftime("%A, %B %d, %Y")

    # Tasks & Reminders
    tasks = get_tasks(status="pending")
    reminders = get_active_reminders()

    task_summary = f"{len(tasks)} pending task(s)" if tasks else "No pending tasks"
    rem_summary = f"{len(reminders)} scheduled reminder(s)" if reminders else "No reminders today"

    # Top news headline
    articles = fetch_rss_news(RSS_FEEDS["india"], limit=2)
    top_news = articles[0]["title"] if articles else "Markets and global news are updating."

    briefing = (
        f"Good morning! Here is your daily briefing for {date_str}:\n\n"
        f"- Agenda: You have {task_summary} and {rem_summary}.\n"
        f"- Top Headline: {top_news}\n\n"
        f"Have a productive day! Say 'What are my tasks' or 'Play some music' to get started."
    )
    return briefing
