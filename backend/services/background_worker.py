"""
background_worker.py — Proactive background scheduler for reminders, alarms, and stock price alerts.
Runs persistently in the background even when the assistant UI is minimized or hidden.
"""

import threading
import time
from datetime import datetime

from backend.database.db import (
    get_active_reminders,
    update_reminder_status,
    get_alarms,
    get_active_price_alerts,
    mark_price_alert_triggered,
)
from backend.tools.finance_tools import fetch_quote
from backend.core.logger import get_logger
from backend.core.tts_engine import speak

logger = get_logger(__name__)


class BackgroundWorker(threading.Thread):
    """Background monitoring daemon for reminders, alarms, and price alerts."""

    def __init__(self, on_notification_cb=None):
        super().__init__(daemon=True)
        self.on_notification_cb = on_notification_cb
        self._stop_event = threading.Event()

    def run(self):
        logger.info("Background proactive monitoring worker started.")
        while not self._stop_event.is_set():
            try:
                now = datetime.now()
                now_str = now.strftime("%Y-%m-%d %H:%M:%S")
                time_str_12h = now.strftime("%I:%M %p")

                # 1. Check Reminders
                reminders = get_active_reminders()
                for r in reminders:
                    if r["remind_at"] <= now_str:
                        msg = f"Reminder: {r['message']}"
                        logger.info(f"Triggering reminder #{r['id']}: {msg}")
                        update_reminder_status(r["id"], "triggered")
                        speak(f"Reminder: {r['message']}")
                        if self.on_notification_cb:
                            self.on_notification_cb("Reminder Due", r["message"])

                # 2. Check Alarms
                alarms = get_alarms()
                for a in alarms:
                    if a["is_active"] and a["time_str"].strip().upper() == time_str_12h.strip().upper():
                        msg = f"ALARM: {a['label']} ({a['time_str']})"
                        logger.info(f"Triggering alarm #{a['id']}: {msg}")
                        speak(f"Alarm: {a['label']}")
                        if self.on_notification_cb:
                            self.on_notification_cb("Alarm", f"{a['label']} - {a['time_str']}")

                # 3. Check Price Alerts (every 60s)
                if now.second < 15:
                    alerts = get_active_price_alerts()
                    for alert in alerts:
                        sym = alert["symbol"]
                        quote = fetch_quote(sym)
                        if quote:
                            curr_p = quote["price"]
                            target = alert["target_price"]
                            cond = alert["condition"]
                            if (cond == "above" and curr_p >= target) or (cond == "below" and curr_p <= target):
                                alert_msg = f"Price Alert: {sym} is now {curr_p} (Target: {target})"
                                logger.info(alert_msg)
                                mark_price_alert_triggered(alert["id"])
                                speak(alert_msg)
                                if self.on_notification_cb:
                                    self.on_notification_cb("Stock Price Alert", alert_msg)

            except Exception as e:
                logger.error(f"Error in background worker loop: {e}")

            # Sleep in short increments to allow fast shutdown
            for _ in range(20):
                if self._stop_event.is_set():
                    break
                time.sleep(0.5)

    def stop(self):
        self._stop_event.set()


_worker_instance: BackgroundWorker | None = None


def start_background_service(notification_callback=None):
    global _worker_instance
    if _worker_instance is None or not _worker_instance.is_alive():
        _worker_instance = BackgroundWorker(on_notification_cb=notification_callback)
        _worker_instance.start()


def stop_background_service():
    global _worker_instance
    if _worker_instance and _worker_instance.is_alive():
        _worker_instance.stop()
        _worker_instance = None
