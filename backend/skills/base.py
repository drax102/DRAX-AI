"""
backend/skills/base.py — Universal base class and descriptors for modular DRAX skills.
"""

from typing import Dict, Any, List, Optional, Callable


class SkillAction:
    """Represents an actionable method within a Skill."""

    def __init__(
        self,
        name: str,
        handler: Callable,
        description: str = "",
        required_capability: str = "cloud",
        risk_level: str = "low",
        requires_confirmation: bool = False,
    ):
        self.name = name
        self.handler = handler
        self.description = description
        self.required_capability = required_capability
        self.risk_level = risk_level
        self.requires_confirmation = requires_confirmation

    def execute(self, **kwargs) -> Any:
        return self.handler(**kwargs)


class BaseSkill:
    """Base class for all modular skills."""

    name: str = "base"
    category: str = "general"
    required_capability: str = "cloud"

    def __init__(self):
        self.actions: Dict[str, SkillAction] = {}
        self._register_actions()

    def _register_actions(self):
        """Override in subclasses to register SkillActions."""
        pass

    def register_action(
        self,
        name: str,
        handler: Callable,
        description: str = "",
        required_capability: Optional[str] = None,
        risk_level: str = "low",
        requires_confirmation: bool = False,
    ):
        cap = required_capability or self.required_capability
        self.actions[name] = SkillAction(
            name=name,
            handler=handler,
            description=description,
            required_capability=cap,
            risk_level=risk_level,
            requires_confirmation=requires_confirmation,
        )

    def get_action(self, action_name: str) -> Optional[SkillAction]:
        return self.actions.get(action_name)
