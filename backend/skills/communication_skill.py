"""
backend/skills/communication_skill.py — Universal communication skill interface.
Handles voice calls, SMS messages, WhatsApp, and Email with capability checks.
"""

from typing import Optional, Dict, Any
from backend.skills.base import BaseSkill
from backend.core.logger import get_logger

logger = get_logger(__name__)


class CommunicationSkill(BaseSkill):
    name = "communication"
    category = "communication"
    required_capability = "calls"

    def _register_actions(self):
        self.register_action("make_call", self.make_call, "Place a voice call", "calls", risk_level="medium")
        self.register_action("send_sms", self.send_sms, "Send an SMS text message", "sms", risk_level="medium")
        self.register_action("send_whatsapp", self.send_whatsapp, "Send a WhatsApp message", "apps", risk_level="medium")
        self.register_action("send_email", self.send_email, "Draft or send an email", "apps", risk_level="medium")

    def make_call(self, contact: str = "", phone: str = "") -> str:
        target = contact or phone or "contact"
        return f"Initiating voice call to {target}..."

    def send_sms(self, recipient: str = "", message: str = "") -> str:
        return f"Sending SMS to {recipient}: '{message}'"

    def send_whatsapp(self, recipient: str = "", message: str = "") -> str:
        import urllib.parse
        import webbrowser
        msg_enc = urllib.parse.quote(message)
        url = f"https://api.whatsapp.com/send?phone={recipient}&text={msg_enc}" if recipient else f"https://web.whatsapp.com/"
        webbrowser.open(url)
        return f"Opening WhatsApp to message {recipient or 'contact'}."

    def send_email(self, recipient: str = "", subject: str = "", body: str = "") -> str:
        import urllib.parse
        import webbrowser
        mailto = f"mailto:{recipient}?subject={urllib.parse.quote(subject)}&body={urllib.parse.quote(body)}"
        webbrowser.open(mailto)
        return f"Opening email client for {recipient}."


communication_skill = CommunicationSkill()
