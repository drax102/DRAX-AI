"""
settings_dialog.py — Comprehensive settings configuration dialog for DRAX AI.
"""

import json
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QCheckBox,
    QMessageBox,
)

from backend.core.audio_manager import list_input_devices
from backend.core.autostart import is_autostart_enabled, set_autostart
from backend.core.config import settings, _CONFIG_PATH
from backend.core.logger import get_logger
from backend.tools.app_tools import rebuild_app_index

logger = get_logger(__name__)


class SettingsDialog(QDialog):
    """Settings modal dialog for configuring assistant parameters."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("DRAX AI — Configuration & Settings")
        self.resize(500, 520)
        self.setStyleSheet("""
            QDialog {
                background-color: #080b10;
                color: #e6f1ff;
                font-family: 'Segoe UI', sans-serif;
            }
            QLabel {
                color: #8b949e;
                font-weight: bold;
            }
            QLineEdit, QComboBox, QSpinBox {
                background-color: #0d1117;
                color: #00f3ff;
                border: 1px solid #1f2937;
                border-radius: 4px;
                padding: 6px;
            }
            QPushButton {
                background-color: #0f1923;
                color: #00f3ff;
                border: 1px solid #00f3ff;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #00f3ff;
                color: #080b10;
            }
        """)

        self._build_ui()
        self._load_current_settings()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        form = QFormLayout()
        form.setSpacing(12)

        # Assistant Name
        self.name_edit = QLineEdit()
        form.addRow("Assistant Name:", self.name_edit)

        # Wake Word
        self.wake_edit = QLineEdit()
        form.addRow("Wake Word:", self.wake_edit)

        # Microphone Dropdown
        self.mic_combo = QComboBox()
        self.mic_combo.addItem("Auto (System Default)", "auto")
        for dev in list_input_devices():
            self.mic_combo.addItem(f"{dev['name']} (#{dev['index']})", str(dev["index"]))
        form.addRow("Microphone Device:", self.mic_combo)

        # TTS Speed
        self.tts_speed = QSpinBox()
        self.tts_speed.setRange(100, 300)
        self.tts_speed.setValue(185)
        form.addRow("Voice Rate (WPM):", self.tts_speed)

        # Default Weather Location
        self.weather_edit = QLineEdit()
        form.addRow("Default Weather City:", self.weather_edit)

        # Start with Windows
        self.autostart_check = QCheckBox("Start automatically on Windows boot (Always-On)")
        form.addRow("Windows Startup:", self.autostart_check)

        # Notifications
        self.notif_check = QCheckBox("Show Windows Notification Popups")
        form.addRow("Notifications:", self.notif_check)

        # Rebuild app index button
        self.reindex_btn = QPushButton("🔄 Rebuild Application Index")
        self.reindex_btn.clicked.connect(self._on_reindex)
        form.addRow("App Index:", self.reindex_btn)

        layout.addLayout(form)

        # Save / Cancel Buttons
        btn_box = QHBoxLayout()
        self.save_btn = QPushButton("Save Settings")
        self.save_btn.clicked.connect(self._save_settings)
        btn_box.addWidget(self.save_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        btn_box.addWidget(self.cancel_btn)

        layout.addLayout(btn_box)

    def _load_current_settings(self):
        self.name_edit.setText(settings.get("assistant", "name", "Drax"))
        self.wake_edit.setText(settings.get("assistant", "wake_word", "hey drax"))
        self.tts_speed.setValue(settings.get("tts", "rate", 185))
        self.autostart_check.setChecked(is_autostart_enabled())
        self.notif_check.setChecked(settings.get("ui", "show_notifications", True))
        self.weather_edit.setText("Delhi")

    def _on_reindex(self):
        self.reindex_btn.setEnabled(False)
        self.reindex_btn.setText("Scanning...")
        try:
            msg = rebuild_app_index()
            QMessageBox.information(self, "App Index Rebuilt", msg)
        finally:
            self.reindex_btn.setEnabled(True)
            self.reindex_btn.setText("🔄 Rebuild Application Index")

    def _save_settings(self):
        try:
            # Set Windows Autostart
            set_autostart(self.autostart_check.isChecked())

            data = {
                "assistant": {
                    "name": self.name_edit.text().strip() or "Drax",
                    "wake_word": self.wake_edit.text().strip() or "hey drax",
                },
                "tts": {
                    "rate": self.tts_speed.value(),
                },
                "ui": {
                    "show_notifications": self.notif_check.isChecked(),
                },
                "startup": {
                    "start_with_windows": self.autostart_check.isChecked(),
                },
            }
            # Save to config/settings.json
            with open(_CONFIG_PATH, "r+", encoding="utf-8") as f:
                curr = json.load(f)
                curr.setdefault("assistant", {}).update(data["assistant"])
                curr.setdefault("tts", {}).update(data["tts"])
                curr.setdefault("ui", {}).update(data["ui"])
                curr.setdefault("startup", {}).update(data["startup"])
                f.seek(0)
                json.dump(curr, f, indent=2)
                f.truncate()

            QMessageBox.information(self, "Success", "Settings saved successfully.")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save settings: {e}")
