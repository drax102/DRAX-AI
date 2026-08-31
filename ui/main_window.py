"""
main_window.py — Main Cybernetic Virtual Assistant GUI Window for DRAX AI.
Features animated virtual avatar HUD, chat terminal, quick action buttons, settings dialog,
background worker integration, cloud connector, and confirmation approval gates.
"""

import html
import os
import sys
import threading

from PyQt5.QtCore import QThread, QTimer, Qt, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QCloseEvent, QFont, QIcon
from PyQt5.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from backend.agent.agent import agent
from backend.agent.context import context
from backend.core.app_indexer import scan_and_rebuild_index
from backend.core.assistant import AssistantState, assistant
from backend.core.audio_manager import test_microphone
from backend.core.command_processor import process_command_async
from backend.core.config import settings
from backend.core.logger import get_logger
from backend.core.speech_recognizer import listen_for_command_speech
from backend.core.system_info import get_system_telemetry
from backend.core.wake_word import listen_for_wake_word
from backend.services.background_worker import start_background_service, stop_background_service
from backend.services.cloud_connector import cloud_connector
from backend.services.api_service import run_api_server
from ui.anime_avatar import DraxAvatarWidget
from ui.settings_dialog import SettingsDialog
from ui.styles import CYBER_STYLE
from ui.tray import DraxSystemTray

logger = get_logger(__name__)


# ─── Worker Threads ─────────────────────────────────────────────────────────

class WakeWordWorker(QThread):
    """Background thread listening for 'Hey Drax' wake word."""

    wake_detected = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._stop_event = threading.Event()

    def run(self):
        def _on_wake():
            self.wake_detected.emit()

        listen_for_wake_word(_on_wake, stop_event=self._stop_event)

    def stop(self):
        self._stop_event.set()
        self.wait(1500)


class SpeechCaptureWorker(QThread):
    """Worker for listening to post-wake command speech."""

    speech_captured = pyqtSignal(str)

    def run(self):
        text = listen_for_command_speech()
        self.speech_captured.emit(text)


# ─── Main GUI Window ────────────────────────────────────────────────────────

class DraxWindow(QWidget):
    """Main Cybernetic HUD Window for Drax AI."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("DRAX AI — Cybernetic Personal Assistant")
        self.resize(1050, 700)
        self.setStyleSheet(CYBER_STYLE)

        self.wake_worker: WakeWordWorker | None = None
        self.speech_worker: SpeechCaptureWorker | None = None
        self.cmd_worker = None
        self.is_compact_mode = False

        # System tray
        self.tray = DraxSystemTray(self)
        self.tray.toggle_window_requested.connect(self.toggle_visibility)
        self.tray.toggle_listening_requested.connect(self._toggle_wake_listening)
        self.tray.reindex_requested.connect(self._reindex_apps)
        self.tray.mic_test_requested.connect(self._test_mic)
        self.tray.settings_requested.connect(self._open_settings)
        self.tray.exit_requested.connect(self._force_exit)
        self.tray.show()

        self._build_ui()

        # Connect Assistant state machine signals
        assistant.state_changed.connect(self._on_assistant_state_changed)
        assistant.speech_detected.connect(self._on_speech_detected)
        assistant.response_ready.connect(self._on_response_ready)

        # Telemetry Timer (every 2 seconds)
        self.telemetry_timer = QTimer(self)
        self.telemetry_timer.timeout.connect(self._update_telemetry)
        self.telemetry_timer.start(2000)

        # Start wake-word listener
        self._start_wake_word_listener()

        # Start Proactive Background Scheduler & REST API
        start_background_service(notification_callback=self._on_background_notification)
        run_api_server(port=8765)

        # Start Cloud Connector (Background relay to web dashboard)
        cloud_connector.start()

        self._append_system_message("DRAX AI v2 online. Say 'Hey Drax' or type any command.")

    def _build_ui(self):
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.setSpacing(15)

        # ── Left Column: Cybernetic Avatar + Telemetry ─────────────────────
        self.left_col = QVBoxLayout()
        self.left_col.setSpacing(15)

        # Animated Cybernetic Avatar Widget
        self.avatar = DraxAvatarWidget(self)
        self.left_col.addWidget(self.avatar, alignment=Qt.AlignCenter)

        # Telemetry Table
        self.telemetry_table = QTableWidget(5, 2)
        self.telemetry_table.setHorizontalHeaderLabels(["Metric", "Value"])
        self.telemetry_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.telemetry_table.verticalHeader().setVisible(False)
        self.telemetry_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.left_col.addWidget(self.telemetry_table)

        # Microphone Push-To-Talk Button
        self.mic_btn = QPushButton("🎤 TALK TO DRAX")
        self.mic_btn.setObjectName("MicBtn")
        self.mic_btn.clicked.connect(self._trigger_voice_capture)
        self.left_col.addWidget(self.mic_btn)

        self.main_layout.addLayout(self.left_col, stretch=1)

        # ── Right Column: Chat Terminal & Action Controls ──────────────────
        self.right_col = QVBoxLayout()
        self.right_col.setSpacing(10)

        # Chat Output Window
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setFont(QFont("Consolas", 10))
        self.right_col.addWidget(self.chat_display, stretch=1)

        # Confirmation Action Bar (Hidden by default)
        self.confirm_frame = QFrame()
        self.confirm_frame.setStyleSheet("background-color: #1a1600; border: 1px solid #ffd700; border-radius: 4px; padding: 4px;")
        confirm_layout = QHBoxLayout(self.confirm_frame)
        self.confirm_label = QLineEdit("Action requires confirmation.")
        self.confirm_label.setReadOnly(True)
        self.confirm_label.setStyleSheet("color: #ffd700; font-weight: bold; background: transparent; border: none;")
        confirm_layout.addWidget(self.confirm_label, stretch=1)

        self.btn_confirm_yes = QPushButton("✔ Confirm")
        self.btn_confirm_yes.setStyleSheet("background-color: #00ff88; color: #080b10; font-weight: bold; padding: 6px 14px;")
        self.btn_confirm_yes.clicked.connect(lambda: self._submit_command("yes"))
        confirm_layout.addWidget(self.btn_confirm_yes)

        self.btn_confirm_no = QPushButton("✖ Cancel")
        self.btn_confirm_no.setStyleSheet("background-color: #ff3366; color: #ffffff; font-weight: bold; padding: 6px 14px;")
        self.btn_confirm_no.clicked.connect(lambda: self._submit_command("no"))
        confirm_layout.addWidget(self.btn_confirm_no)

        self.confirm_frame.hide()
        self.right_col.addWidget(self.confirm_frame)

        # Input Row
        input_row = QHBoxLayout()
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Type command (e.g. 'search AI news and summarize', 'what is Apple stock')...")
        self.input_field.returnPressed.connect(self._handle_text_input)
        input_row.addWidget(self.input_field, stretch=1)

        self.send_btn = QPushButton("SEND")
        self.send_btn.clicked.connect(self._handle_text_input)
        input_row.addWidget(self.send_btn)

        self.right_col.addLayout(input_row)

        # Quick Actions Row
        quick_row = QHBoxLayout()

        btn_brief = QPushButton("🌅 Daily Brief")
        btn_brief.clicked.connect(lambda: self._submit_command("give me my daily briefing"))
        quick_row.addWidget(btn_brief)

        btn_tasks = QPushButton("📋 My Tasks")
        btn_tasks.clicked.connect(lambda: self._submit_command("what are my tasks"))
        quick_row.addWidget(btn_tasks)

        btn_watchlist = QPushButton("📈 Watchlist")
        btn_watchlist.clicked.connect(lambda: self._submit_command("show watchlist"))
        quick_row.addWidget(btn_watchlist)

        btn_settings = QPushButton("⚙️ Settings")
        btn_settings.clicked.connect(self._open_settings)
        quick_row.addWidget(btn_settings)

        btn_compact = QPushButton("🗗 Compact")
        btn_compact.clicked.connect(self._toggle_compact_mode)
        quick_row.addWidget(btn_compact)

        self.right_col.addLayout(quick_row)

        self.main_layout.addLayout(self.right_col, stretch=2)

    # ── Wake Word & Voice Logic ─────────────────────────────────────────────

    def _start_wake_word_listener(self):
        if self.wake_worker and self.wake_worker.isRunning():
            return
        self.wake_worker = WakeWordWorker()
        self.wake_worker.wake_detected.connect(self._on_wake_word_triggered)
        self.wake_worker.start()

    @pyqtSlot()
    def _on_wake_word_triggered(self):
        logger.info("Wake word triggered — waking assistant from background")
        if not self.isVisible():
            self.show()
            self.raise_()
            self.activateWindow()

        self.tray.notify("Drax Listening", "Listening for your command...")
        self._trigger_voice_capture()

    def _trigger_voice_capture(self):
        if self.speech_worker and self.speech_worker.isRunning():
            return

        assistant.set_state(AssistantState.LISTENING)
        self.speech_worker = SpeechCaptureWorker()
        self.speech_worker.speech_captured.connect(self._on_speech_captured)
        self.speech_worker.start()

    @pyqtSlot(str)
    def _on_speech_captured(self, text: str):
        if text:
            self._append_user_message(f"🎤 {text}")
            self._submit_command(text)
        else:
            assistant.set_state(AssistantState.IDLE)
            self._append_system_message("No speech detected.")

    # ── Command Handling ────────────────────────────────────────────────────

    def _handle_text_input(self):
        text = self.input_field.text().strip()
        if not text:
            return
        self.input_field.clear()
        self._append_user_message(text)
        self._submit_command(text)

    def _submit_command(self, command_text: str):
        if self.cmd_worker and self.cmd_worker.isRunning():
            return

        self.confirm_frame.hide()
        self.cmd_worker = process_command_async(command_text)

    # ── Signal Handlers ─────────────────────────────────────────────────────

    @pyqtSlot(object)
    def _on_assistant_state_changed(self, state: AssistantState):
        self.avatar.set_state(state.value)
        if state == AssistantState.LISTENING:
            self.mic_btn.setText("🔴 LISTENING...")
            self.mic_btn.setEnabled(False)
        else:
            self.mic_btn.setText("🎤 TALK TO DRAX")
            self.mic_btn.setEnabled(True)

    @pyqtSlot(str)
    def _on_speech_detected(self, text: str):
        pass

    @pyqtSlot(str)
    def _on_response_ready(self, text: str):
        self._append_drax_message(text)
        if context.pending_confirmation:
            self.confirm_frame.show()
            self.confirm_label.setText(f"Confirmation: {context.pending_confirmation['tool'].replace('_', ' ').upper()}")

    def _on_background_notification(self, title: str, message: str):
        self.tray.notify(title, message)
        self._append_system_message(f"[{title}] {message}")

    # ── Chat Formatting ─────────────────────────────────────────────────────

    def _append_user_message(self, text: str):
        safe_text = html.escape(text)
        self.chat_display.append(
            f'<div style="margin: 4px 0;"><span style="color: #00f3ff; font-weight: bold;">YOU &gt;</span> {safe_text}</div>'
        )

    def _append_drax_message(self, text: str):
        safe_text = html.escape(text)
        self.chat_display.append(
            f'<div style="margin: 4px 0;"><span style="color: #00ff88; font-weight: bold;">DRAX &gt;</span> {safe_text}</div>'
        )

    def _append_system_message(self, text: str):
        safe_text = html.escape(text)
        self.chat_display.append(
            f'<div style="margin: 4px 0; color: #8b949e; font-style: italic;">[SYS] {safe_text}</div>'
        )

    # ── Telemetry & Actions ─────────────────────────────────────────────────

    def _update_telemetry(self):
        data = get_system_telemetry()
        cloud_status = "Online (Paired)" if cloud_connector.is_connected else "Local Standalone"
        metrics = [
            ("CPU Usage", f"{data.get('cpu_percent', 0)}%"),
            ("RAM Usage", f"{data.get('ram_percent', 0)}% ({data.get('ram_used_gb', 0)} GB)"),
            ("Workstation", f"{data.get('os_name', 'Windows')}"),
            ("Cloud Status", cloud_status),
            ("Agent State", assistant.state.value),
        ]
        for row, (k, v) in enumerate(metrics):
            self.telemetry_table.setItem(row, 0, QTableWidgetItem(k))
            self.telemetry_table.setItem(row, 1, QTableWidgetItem(v))

    def _reindex_apps(self):
        self._append_system_message("Rebuilding application index in background...")
        threading.Thread(target=scan_and_rebuild_index, daemon=True).start()

    def _test_mic(self):
        self._append_system_message("Testing microphone for 3 seconds...")

        def _do_test():
            ok = test_microphone(3.0)
            msg = "Microphone test passed!" if ok else "Microphone test failed — check logs."
            self._append_system_message(msg)

        threading.Thread(target=_do_test, daemon=True).start()

    def _open_settings(self):
        dlg = SettingsDialog(self)
        dlg.exec_()

    def _toggle_compact_mode(self):
        if not self.is_compact_mode:
            self.chat_display.hide()
            self.telemetry_table.hide()
            self.resize(320, 360)
            self.is_compact_mode = True
        else:
            self.chat_display.show()
            self.telemetry_table.show()
            self.resize(1050, 700)
            self.is_compact_mode = False

    def _toggle_wake_listening(self):
        if self.wake_worker and self.wake_worker.isRunning():
            self.wake_worker.stop()
            self.wake_worker = None
            self._append_system_message("Wake word listening paused from system tray.")
        else:
            self._start_wake_word_listener()
            self._append_system_message("Wake word listening resumed from system tray.")

    def toggle_visibility(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.raise_()
            self.activateWindow()

    def _force_exit(self):
        logger.info("Stopping and exiting Drax AI from System Tray...")
        try:
            cloud_connector.stop()
        except Exception:
            pass
        try:
            stop_background_service()
        except Exception:
            pass
        if self.wake_worker:
            try:
                self.wake_worker.stop()
            except Exception:
                pass
        if self.speech_worker and self.speech_worker.isRunning():
            try:
                self.speech_worker.terminate()
            except Exception:
                pass
        self.tray.hide()
        QApplication.quit()
        os._exit(0)

    def closeEvent(self, event: QCloseEvent):
        """Minimize to system tray on window close so Drax stays listening in background."""
        event.ignore()
        self.hide()
        self.tray.notify("Drax Active", "Running in background. Say 'Hey Drax' to activate.")


# Aliases
DraxUI = DraxWindow
JarvisUI = DraxWindow
