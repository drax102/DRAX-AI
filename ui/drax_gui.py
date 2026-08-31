import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTextEdit, QLineEdit, QPushButton, 
                             QLabel, QFrame)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QIcon, QFont

from ui.visualizer import DraxVisualizer
from ui.styles import CYBER_STYLE
from backend.core.intent_router import route_command
from backend.core.command_listener import listen_for_command_speech
from backend.core.wake_word import listen_for_wake_word
from backend.core.tts_engine import get_voice_engine
from backend.core.system_info import get_system_telemetry


class WakeWordWorker(QThread):
    wake_triggered = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._running = True

    def run(self):
        def on_wake():
            if self._running:
                self.wake_triggered.emit()

        try:
            listen_for_wake_word(on_wake)
        except Exception as e:
            print(f"⚠️ Wake word worker thread notice: {e}")

    def stop(self):
        self._running = False


class SpeechCaptureWorker(QThread):
    speech_captured = pyqtSignal(str)

    def run(self):
        try:
            text = listen_for_command_speech(timeout=5, phrase_limit=7)
            self.speech_captured.emit(text)
        except Exception as e:
            print(f"⚠️ Speech capture worker notice: {e}")
            self.speech_captured.emit("")


class DraxWindow(QMainWindow):
    """
    Main Cybernetic UI Window for DRAX AI.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DRAX AI v2.0 // Cybernetic Intelligence")
        self.resize(650, 780)
        self.setMinimumSize(540, 640)

        # Apply Cyber Theme
        self.setStyleSheet(CYBER_STYLE)

        # Initialize Non-Blocking Voice Engine
        self.voice_engine = get_voice_engine()
        self.voice_engine.speech_started.connect(self._on_speech_started)
        self.voice_engine.speech_finished.connect(self._on_speech_finished)

        # UI Setup
        self._init_ui()

        # Background Wake Word Listener
        self.wake_thread = WakeWordWorker()
        self.wake_thread.wake_triggered.connect(self.handle_voice_trigger)
        self.wake_thread.start()

        # Telemetry Timer (CPU/RAM updates)
        self.telemetry_timer = QTimer(self)
        self.telemetry_timer.timeout.connect(self._update_telemetry)
        self.telemetry_timer.start(2000)

        # Initial Welcome Message
        self._append_message("DRAX", "Greetings. I am DRAX, your cybernetic assistant. Type or click the mic button to issue commands.")
        self.voice_engine.speak("Greetings. I am DRAX, your cybernetic assistant.")

    def _init_ui(self):
        central_widget = QWidget()
        central_widget.setObjectName("CentralWidget")
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(10)

        # 1. Header Frame
        header_frame = QFrame()
        header_frame.setObjectName("HeaderFrame")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(14, 10, 14, 10)

        title_vbox = QVBoxLayout()
        title_label = QLabel("⚡ DRAX AI v2.0")
        title_label.setObjectName("TitleLabel")
        subtitle_label = QLabel("// CYBERNETIC ASSISTANT ENGINE")
        subtitle_label.setObjectName("SubtitleLabel")
        title_vbox.addWidget(title_label)
        title_vbox.addWidget(subtitle_label)

        self.stat_label = QLabel("CPU 0% | RAM 0%")
        self.stat_label.setObjectName("StatLabel")

        header_layout.addLayout(title_vbox)
        header_layout.addStretch()
        header_layout.addWidget(self.stat_label)

        # 2. Central HUD Visualizer Widget
        self.visualizer = DraxVisualizer()
        self.visualizer.setFixedSize(220, 200)

        vis_container = QHBoxLayout()
        vis_container.addStretch()
        vis_container.addWidget(self.visualizer)
        vis_container.addStretch()

        # 3. Sci-Fi Chat Terminal Log
        self.chat_terminal = QTextEdit()
        self.chat_terminal.setObjectName("ChatTerminal")
        self.chat_terminal.setReadOnly(True)

        # 4. Quick Action HUD Control Bar
        hud_bar = QHBoxLayout()
        hud_bar.setSpacing(8)

        self.mic_btn = QPushButton("🎤 VOICE")
        self.mic_btn.setObjectName("MicBtn")
        self.mic_btn.clicked.connect(self.handle_voice_trigger)

        btn_search = QPushButton("🌐 Search")
        btn_search.clicked.connect(lambda: self.process_command("search python news"))

        btn_status = QPushButton("💻 System")
        btn_status.clicked.connect(lambda: self.process_command("system status"))

        btn_weather = QPushButton("🌤️ Weather")
        btn_weather.clicked.connect(lambda: self.process_command("weather in Mumbai"))

        btn_reindex = QPushButton("⚡ Reindex")
        btn_reindex.clicked.connect(lambda: self.process_command("reindex"))

        btn_clear = QPushButton("🧹 Clear")
        btn_clear.clicked.connect(self.chat_terminal.clear)

        hud_bar.addWidget(self.mic_btn)
        hud_bar.addWidget(btn_search)
        hud_bar.addWidget(btn_status)
        hud_bar.addWidget(btn_weather)
        hud_bar.addWidget(btn_reindex)
        hud_bar.addWidget(btn_clear)

        # 5. Bottom Input Field
        input_layout = QHBoxLayout()
        self.cmd_input = QLineEdit()
        self.cmd_input.setObjectName("CommandInput")
        self.cmd_input.setPlaceholderText("Type command (e.g. 'open Chrome', 'weather', 'system status')...")
        self.cmd_input.returnPressed.connect(self.handle_text_submit)

        send_btn = QPushButton("EXECUTE ▶")
        send_btn.clicked.connect(self.handle_text_submit)

        input_layout.addWidget(self.cmd_input, 4)
        input_layout.addWidget(send_btn, 1)

        # Assemble layout
        main_layout.addWidget(header_frame)
        main_layout.addLayout(vis_container)
        main_layout.addWidget(self.chat_terminal, 1)
        main_layout.addLayout(hud_bar)
        main_layout.addLayout(input_layout)

        self.setCentralWidget(central_widget)

    def _update_telemetry(self):
        try:
            t = get_system_telemetry()
            self.stat_label.setText(f"CPU {t['cpu_usage']:.0f}% | RAM {t['ram_usage']:.0f}%")
        except Exception:
            pass

    def _append_message(self, sender: str, text: str):
        if sender == "USER":
            html = f'<div style="margin: 6px 0;"><span style="color:#00FF99; font-weight:bold;">&gt; USER:</span> <span style="color:#F1F5F9;">{text}</span></div>'
        else:
            html = f'<div style="margin: 6px 0; background: #0F172A; border-left: 3px solid #00F3FF; padding: 6px 10px; border-radius: 6px;"><span style="color:#00F3FF; font-weight:bold;">⚡ DRAX:</span> <span style="color:#E2E8F0;">{text}</span></div>'
        self.chat_terminal.append(html)

    def handle_text_submit(self):
        cmd = self.cmd_input.text().strip()
        if not cmd:
            return
        self.cmd_input.clear()
        self.process_command(cmd)

    def handle_voice_trigger(self):
        self.visualizer.set_state(DraxVisualizer.STATE_LISTENING)
        self.mic_btn.setText("🎤 LISTENING...")
        self.mic_btn.setEnabled(False)

        self.speech_worker = SpeechCaptureWorker()
        self.speech_worker.speech_captured.connect(self._on_speech_captured)
        self.speech_worker.start()

    def _on_speech_captured(self, command_text: str):
        self.mic_btn.setText("🎤 VOICE")
        self.mic_btn.setEnabled(True)

        if command_text:
            self.process_command(command_text)
        else:
            self.visualizer.set_state(DraxVisualizer.STATE_IDLE)
            self._append_message("DRAX", "I didn't hear a command. Please try speaking again or type.")

    def process_command(self, command_text: str):
        self._append_message("USER", command_text)
        self.visualizer.set_state(DraxVisualizer.STATE_PROCESSING)
        QApplication.processEvents()

        response = route_command(command_text)

        self._append_message("DRAX", response)
        self.voice_engine.speak(response)

    def _on_speech_started(self, text: str):
        self.visualizer.set_state(DraxVisualizer.STATE_SPEAKING)

    def _on_speech_finished(self):
        self.visualizer.set_state(DraxVisualizer.STATE_IDLE)

    def closeEvent(self, event):
        if hasattr(self, 'wake_thread'):
            self.wake_thread.stop()
            try:
                self.wake_thread.terminate()
            except Exception:
                pass
        event.accept()


def main():
    app = QApplication(sys.argv)
    window = DraxWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
