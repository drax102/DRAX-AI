"""
planner.py — Multi-step task planner and natural language intent parser.
Decomposes compound sentences and multi-step directives into executable tool action sequences.
"""

import re
from typing import List, Dict, Any, Optional

from backend.agent.context import context
from backend.agent.tool_registry import registry
from backend.core.logger import get_logger

logger = get_logger(__name__)


class ActionStep:
    def __init__(self, tool_name: str, args: Dict[str, Any], description: str = ""):
        self.tool_name = tool_name
        self.args = args
        self.description = description

    def to_dict(self) -> dict:
        return {"tool": self.tool_name, "args": self.args, "description": self.description}


class ExecutionPlan:
    def __init__(self, raw_input: str, steps: List[ActionStep]):
        self.raw_input = raw_input
        self.steps = steps

    @property
    def is_empty(self) -> bool:
        return len(self.steps) == 0


def _parse_single_clause(clause: str) -> Optional[ActionStep]:
    """Parse an individual sub-clause into an ActionStep."""
    c = clause.strip().lower()
    if not c:
        return None

    # Check contextual follow-up first
    follow_up = context.resolve_follow_up(c)
    if follow_up:
        tool_name, kwargs = follow_up
        return ActionStep(tool_name=tool_name, args=kwargs, description=clause)

    # 1. Identity & Telemetry
    if c in ["who are you", "what is your name", "identify yourself"]:
        return ActionStep(tool_name="get_telemetry", args={}, description="Identify self")

    if any(k in c for k in ["system status", "telemetry", "cpu usage", "ram usage", "memory usage"]):
        return ActionStep(tool_name="get_telemetry", args={}, description="Get telemetry")

    # 2. Workstation Lock / Power
    if any(k in c for k in ["block computer", "lock computer", "lock pc", "lock screen", "lock workstation"]):
        return ActionStep(tool_name="lock_pc", args={}, description="Lock PC")

    if "shutdown" in c or "power off" in c:
        return ActionStep(tool_name="shutdown_pc", args={}, description="Shutdown PC")

    if "restart" in c or "reboot" in c:
        return ActionStep(tool_name="restart_pc", args={}, description="Restart PC")

    if "screenshot" in c or "take a screenshot" in c:
        return ActionStep(tool_name="take_screenshot", args={}, description="Capture screenshot")

    # 3. Daily Briefing
    if any(k in c for k in ["morning briefing", "daily briefing", "good morning drax", "my briefing", "give me my briefing"]):
        return ActionStep(tool_name="get_daily_briefing", args={}, description="Daily briefing")

    # 4. Explicit Web Search (High priority: "search AI news on Google", "can you search recipe for...")
    if any(c.startswith(p) for p in ["search ", "search for ", "can you search ", "please search ", "look up ", "google "]):
        q = c
        for prefix in [
            "can you search for the ", "can you search for ", "can you search the ", "can you search ",
            "please search for the ", "please search for ", "please search the ", "please search ",
            "search for the ", "search for ", "search the ", "search ", "look up ", "google "
        ]:
            if q.startswith(prefix):
                q = q[len(prefix):].strip()
                break
        m = re.search(r"^(.+?)(?:\s+on\s+(\w+))?$", q)
        query = m.group(1).strip() if m else q
        engine = m.group(2) if (m and m.group(2)) else "google"
        return ActionStep(tool_name="search_web", args={"query": query, "engine": engine}, description=f"Search {query}")

    # 5. Alarms
    if "alarm" in c or "wake me up" in c:
        if any(k in c for k in ["show", "list", "what", "check", "get", "view", "see", "my alarm"]):
            return ActionStep(tool_name="list_alarms", args={}, description="List alarms")
        if any(k in c for k in ["cancel", "delete", "remove", "turn off", "stop"]):
            q = re.sub(r"(?:cancel|delete|remove|turn off|stop)\s+(?:the\s+)?alarm", "", c).strip()
            return ActionStep(tool_name="cancel_alarm", args={"query": q}, description="Cancel alarm")
        return ActionStep(tool_name="create_alarm", args={"time_expr": clause}, description="Create alarm")

    # 6. Reminders
    if "remind me" in c or "set a reminder" in c or "reminder" in c:
        if any(k in c for k in ["delete", "cancel", "remove"]):
            q = re.sub(r"(?:delete|cancel|remove)\s+reminder(?:\s+to)?", "", c).strip()
            return ActionStep(tool_name="delete_reminder", args={"query": q}, description="Delete reminder")
        if any(k in c for k in ["list", "what are", "show", "my reminders"]):
            return ActionStep(tool_name="list_reminders", args={}, description="List reminders")
        return ActionStep(tool_name="create_reminder", args={"message": clause}, description="Create reminder")

    # 7. Tasks
    if any(k in c for k in ["task", "todo"]):
        if any(k in c for k in [
            "what are my task", "what are my tasks", "my tasks", "my task",
            "list tasks", "list task", "show tasks", "show task", "all tasks",
            "get tasks", "show me tasks", "show me my tasks", "show me my task", "show me the tasks", "show the task"
        ]):
            return ActionStep(tool_name="list_tasks", args={}, description="List tasks")

        m_add = re.search(r"(?:add|create)\s+(?:a\s+)?task(?:\s+to)?\s+(.+)$", c)
        if m_add:
            return ActionStep(tool_name="create_task", args={"title": m_add.group(1).strip()}, description="Create task")

        m_comp = re.search(r"(?:complete|finish|mark|done with)\s+(?:task\s+)?(.+)$", c)
        if m_comp and "add" not in c:
            return ActionStep(tool_name="complete_task", args={"query": m_comp.group(1).strip()}, description="Complete task")

        m_del = re.search(r"(?:delete|remove)\s+task(?:\s+to)?\s+(.+)$", c)
        if m_del:
            return ActionStep(tool_name="delete_task", args={"query": m_del.group(1).strip()}, description="Delete task")

    # 8. News
    if "news" in c or "headlines" in c:
        topic = "world"
        if "india" in c or "indian" in c: topic = "india"
        elif "delhi" in c: topic = "delhi"
        elif "punjab" in c: topic = "punjab"
        elif "ai" in c or "artificial intelligence" in c: topic = "ai"
        elif "tech" in c or "technology" in c: topic = "technology"
        elif "stock" in c or "business" in c or "market" in c or "finance" in c: topic = "business"
        return ActionStep(tool_name="get_news", args={"topic_or_region": topic}, description=f"News for {topic}")

    # 9. Stocks & Financial Quotes
    if "track " in c and not any(w in c for w in ["next track", "previous track"]):
        sym = c.replace("track ", "").replace("stock", "").replace("for me", "").strip()
        return ActionStep(tool_name="track_stock", args={"symbol": sym}, description=f"Track {sym}")

    if any(k in c for k in ["watchlist", "tracked stocks", "show watchlist"]):
        return ActionStep(tool_name="list_watchlist", args={}, description="List stock watchlist")

    if any(k in c for k in ["stock", "share price", "share of", "price of", "nifty", "sensex", "bitcoin", "crypto"]):
        sym = c
        if any(k in sym for k in ["stock of india", "indian stock", "india stock", "indian market"]):
            return ActionStep(tool_name="get_stock_price", args={"symbol": "^NSEI"}, description="Nifty 50 Index")
        for w in [
            "what is the stock price of", "what is the share price of", "what's the stock price of", "what's the share price of",
            "share price of", "stock price of", "what is the price of", "what's the price of",
            "what is", "what's", "how is", "show me", "check", "price of", "share of", "stock price", "share price", "stock", "share", "recent"
        ]:
            sym = sym.replace(w, "").strip()
        sym = sym.replace("?", "").strip()
        return ActionStep(tool_name="get_stock_price", args={"symbol": sym}, description=f"Stock price for {sym}")

    # 10. Weather
    if "weather" in c or "temperature" in c or "will it rain" in c:
        city = "Delhi"
        m = re.search(r"\b(?:in|for|at)\s+([a-zA-Z\s]+)", c)
        if m:
            city = m.group(1).strip()
        else:
            city_clean = re.sub(r"^(?:what is|what's|how is|check|show me)?\s*(?:the)?\s*(?:weather|temperature)(?:\s+in)?\s*", "", c).strip()
            if city_clean:
                city = city_clean
        return ActionStep(tool_name="get_weather", args={"city": city}, description=f"Weather in {city}")

    # 11. Media & Playback Controls
    if c in ["pause", "pause music", "pause song", "resume", "resume music", "resume song", "toggle music", "stop music"]:
        return ActionStep(tool_name="pause_media", args={}, description="Pause/resume media")

    if any(k in c for k in ["next song", "next track", "skip song", "skip track"]):
        return ActionStep(tool_name="next_track", args={}, description="Next track")

    if any(k in c for k in ["previous song", "previous track", "last song", "last track"]):
        return ActionStep(tool_name="previous_track", args={}, description="Previous track")

    if c.startswith("play ") or "play some " in c or "listen to " in c:
        q = re.sub(r"^(?:play|listen to|play some)\s+", "", c).strip()
        if q.lower() in ["song", "music", "song on spotify", "music on spotify", "spotify"]:
            return ActionStep(tool_name="pause_media", args={}, description="Toggle media playback")
        platform = "youtube" if "on youtube" in q else "spotify"
        return ActionStep(tool_name="play_media", args={"query": q, "platform": platform}, description=f"Play {q}")

    if "volume" in c or "mute" in c or "unmute" in c:
        act = "down" if "down" in c or "lower" in c or "quieter" in c else ("mute" if "mute" in c else "up")
        return ActionStep(tool_name="volume_control", args={"action": act}, description="Adjust volume")

    # 12. General Knowledge / Wikipedia
    if any(c.startswith(p) for p in ["who is ", "who was ", "what is ", "what was ", "tell me about ", "can you tell me about "]) and not any(w in c for w in ["the weather", "the stock", "my task", "my alarm"]):
        return ActionStep(tool_name="get_knowledge", args={"query": clause}, description=f"Knowledge query for {clause}")

    # 13. Website Opening
    if c.startswith("open website ") or c.startswith("go to ") or c.endswith((".com", ".org", ".io", ".in", ".ai")):
        return ActionStep(tool_name="open_url", args={"url": clause}, description=f"Open website {clause}")

    # 14. App Closing
    if c.startswith("close ") or c.startswith("exit ") or c.startswith("quit ") or c.startswith("terminate "):
        app_to_close = re.sub(r"^(?:close|exit|quit|terminate)\s+", "", c).strip()
        return ActionStep(tool_name="close_app", args={"app_name": app_to_close}, description=f"Close {app_to_close}")

    # 15. File & Folder Operations
    if "open downloads" in c: return ActionStep(tool_name="open_folder", args={"folder_name": "downloads"})
    if "open documents" in c: return ActionStep(tool_name="open_folder", args={"folder_name": "documents"})
    if "open desktop" in c: return ActionStep(tool_name="open_folder", args={"folder_name": "desktop"})
    if "find my " in c or "find file " in c or "search file " in c:
        fname = re.sub(r"^(?:find my|find file|search file|find)\s+", "", c).strip()
        return ActionStep(tool_name="find_file", args={"filename": fname}, description=f"Find file {fname}")

    # 16. App Opening (GTA, Chrome, Spotify, Feedback Hub, etc.)
    if c.startswith("open ") or c.startswith("launch ") or c.startswith("start ") or c.startswith("play game "):
        app_name = re.sub(r"^(?:open|launch|start|play game)\s+", "", c).strip()
        if "." in app_name and not app_name.endswith(".exe"):
            return ActionStep(tool_name="open_url", args={"url": app_name}, description=f"Open site {app_name}")
        return ActionStep(tool_name="open_app", args={"app_name": app_name}, description=f"Open app {app_name}")

    # Fallback to general app opening or search
    return ActionStep(tool_name="open_app", args={"app_name": clause}, description=f"Open {clause}")


def plan_request(user_input: str) -> ExecutionPlan:
    """
    Break natural language input into one or more sequential ActionSteps.
    Supports compound sentences with 'and', 'then', 'after that', etc.
    """
    clean = user_input.strip()
    if not clean:
        return ExecutionPlan(raw_input=user_input, steps=[])

    # Split on sequence conjunctions: "then", "and then", "after that"
    clauses = re.split(r"\s+(?:and\s+then|then|after\s+that)\s+", clean, flags=re.IGNORECASE)

    # If only 1 clause, check if split by 'and' is appropriate
    if len(clauses) == 1 and " and " in clean:
        parts = clean.split(" and ")
        action_verbs = ["play", "open", "search", "remind", "set", "close", "tell", "what", "how", "lock", "block"]
        is_multi_step = False
        for p in parts[1:]:
            if any(p.strip().lower().startswith(v) for v in action_verbs):
                is_multi_step = True
                break

        if is_multi_step:
            clauses = parts

    steps = []
    for clause in clauses:
        step = _parse_single_clause(clause)
        if step:
            steps.append(step)

    logger.info(f"Generated execution plan with {len(steps)} step(s) for '{user_input}'")
    return ExecutionPlan(raw_input=user_input, steps=steps)
