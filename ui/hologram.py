from PyQt5.QtWidgets import QWidget, QLabel
from PyQt5.QtCore import Qt, QThread, pyqtSignal

from backend.core.wake_word import listen_for_wake_word
from backend.core.command_listener import listen_for_command
from backend.core.app_executor import open_app


class WakeThread(QThread):
    wake_detected = pyqtSignal()

    def run(self):
        listen_for_wake_word(self.wake_detected.emit)


class CommandThread(QThread):
    command_captured = pyqtSignal(str)

    def run(self):
        command = listen_for_command()
        self.command_captured.emit(command)


class JarvisUI(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Drax AI – Jarvis Cyan")
        self.setGeometry(600, 200, 400, 400)
        self.setStyleSheet("background-color:black;")

        self.label = QLabel("● IDLE", self)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("color: cyan; font-size: 22px;")
        self.label.setGeometry(50, 170, 300, 60)

        # Wake word thread (always running)
        self.wake_thread = WakeThread()
        self.wake_thread.wake_detected.connect(self.on_wake)
        self.wake_thread.start()

        self.command_thread = None

    def on_wake(self):
        # Show listening state
        self.label.setText("● LISTENING")
        self.label.repaint()

        # Start command listener in background
        self.command_thread = CommandThread()
        self.command_thread.command_captured.connect(self.on_command_done)
        self.command_thread.start()

    def on_command_done(self, command):
        print("Executing command:", command)

        # Execute application command
        response = open_app(command)
        print(response)

        # Back to idle
        self.label.setText("● IDLE")
        self.label.repaint()

        # Reset command thread
        self.command_thread = None
