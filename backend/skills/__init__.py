"""
backend/skills — Modular skills package for DRAX AI Universal Assistant.
"""

from backend.skills.base import BaseSkill, SkillAction
from backend.skills.media_skill import MediaSkill, media_skill
from backend.skills.computer_skill import ComputerSkill, computer_skill
from backend.skills.productivity_skill import ProductivitySkill, productivity_skill
from backend.skills.communication_skill import CommunicationSkill, communication_skill
from backend.skills.web_skill import WebSkill, web_skill

__all__ = [
    "BaseSkill",
    "SkillAction",
    "MediaSkill",
    "media_skill",
    "ComputerSkill",
    "computer_skill",
    "ProductivitySkill",
    "productivity_skill",
    "CommunicationSkill",
    "communication_skill",
    "WebSkill",
    "web_skill",
]
