"""
tool_registry.py — Structured tool registry with parameter schemas, risk levels, and confirmation flags.
"""

from typing import Callable, Dict, Any, List, Optional
from backend.core.logger import get_logger

logger = get_logger(__name__)


class Tool:
    """Represents a discrete assistant capability."""

    def __init__(
        self,
        name: str,
        description: str,
        handler: Callable[..., Any],
        parameters: Optional[Dict[str, Any]] = None,
        risk_level: str = "low",  # "low", "medium", "high", "critical"
        requires_confirmation: bool = False,
        category: str = "general",
    ):
        self.name = name
        self.description = description
        self.handler = handler
        self.parameters = parameters or {}
        self.risk_level = risk_level
        self.requires_confirmation = requires_confirmation
        self.category = category

    def execute(self, **kwargs) -> Any:
        try:
            logger.info(f"Executing tool '{self.name}' with args: {kwargs}")
            return self.handler(**kwargs)
        except Exception as e:
            logger.error(f"Error in tool '{self.name}': {e}")
            return f"Failed to execute {self.name}: {str(e)}"


class ToolRegistry:
    """Central registry of all registered assistant tools."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ToolRegistry, cls).__new__(cls)
            cls._instance._tools: Dict[str, Tool] = {}
        return cls._instance

    def register(self, tool: Tool):
        self._tools[tool.name] = tool
        logger.debug(f"Registered tool: {tool.name} (risk={tool.risk_level})")

    def get(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def list_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters,
                "risk_level": t.risk_level,
                "requires_confirmation": t.requires_confirmation,
                "category": t.category,
            }
            for t in self._tools.values()
        ]

    def has_tool(self, name: str) -> bool:
        return name in self._tools


registry = ToolRegistry()


def register_tool(
    name: str,
    description: str,
    parameters: Optional[Dict[str, Any]] = None,
    risk_level: str = "low",
    requires_confirmation: bool = False,
    category: str = "general",
):
    """Decorator to register a function as a tool."""

    def decorator(fn: Callable):
        tool = Tool(
            name=name,
            description=description,
            handler=fn,
            parameters=parameters,
            risk_level=risk_level,
            requires_confirmation=requires_confirmation,
            category=category,
        )
        registry.register(tool)
        return fn

    return decorator
