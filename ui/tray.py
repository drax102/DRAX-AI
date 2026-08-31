"""
tray.py — System tray integration for DRAX AI.
Provides background operations, notification popups, device pairing codes, and quick menu actions.
"""

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtGui import QIcon, QPixmap, QColor, QPainter
from PyQt5.QtWidgets import QAction, QMenu, QSystemTrayIcon, QMessageBox

from backend.core.autostart import is_autostart_enabled, set_autostart
from backend.services.cloud_connector import cloud_connector
from backend.core.logger import get_logger

logger = get_logger(__name__)


def create_tray_icon_pixmap() -> QIcon:
    """Dynamically generate a cyan glowing circle icon for the system tray."""
    pixmap = QPixmap(32, 32)
    pixmap.fill(QColor(0, 0, 0, 0))  # Transparent background

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    # Cyan glowing circle
    painter.setBrush(QColor(0, 243, 255))
    painter.setPen(QColor(8, 11, 16))
    painter.drawEllipse(4, 4, 24, 24)

    # Inner dark dot
    painter.setBrush(QColor(8, 11, 16))
    painter.drawEllipse(12, 12, 8, 8)

    painter.end()
    return QIcon(pixmap)


class DraxSystemTray(QSystemTrayIcon):
    """System tray icon and context menu manager."""

    toggle_window_requested = pyqtSignal()
    toggle_listening_requested = pyqtSignal()
    reindex_requested = pyqtSignal()
    mic_test_requested = pyqtSignal()
    settings_requested = pyqtSignal()
    exit_requested = pyqtSignal()

    def __init__(self, parent=None):
        icon = create_tray_icon_pixmap()
        super().__init__(icon, parent)
        self.setToolTip("DRAX AI — Active in Background")
        self.is_listening_active = True
        self._init_menu()
        self.activated.connect(self._on_activated)

    def _init_menu(self):
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu {
                background-color: #0d1117;
                color: #e6f1ff;
                border: 1px solid #00f3ff;
                font-family: 'Segoe UI', sans-serif;
            }
            QMenu::item {
                padding: 6px 20px;
            }
            QMenu::item:selected {
                background-color: #00f3ff;
                color: #080b10;
            }
        """)

        toggle_act = QAction("👁️ Show / Hide Assistant", self)
        toggle_act.triggered.connect(self.toggle_window_requested.emit)
        menu.addAction(toggle_act)

        self.listen_act = QAction("🔇 Pause Wake Listening", self)
        self.listen_act.triggered.connect(self._on_toggle_listen)
        menu.addAction(self.listen_act)

        pair_act = QAction("🔗 Show Device Pairing Code", self)
        pair_act.triggered.connect(self._show_pairing_code)
        menu.addAction(pair_act)

        menu.addSeparator()

        self.autostart_act = QAction("🚀 Start With Windows", self)
        self.autostart_act.setCheckable(True)
        self.autostart_act.setChecked(is_autostart_enabled())
        self.autostart_act.triggered.connect(self._on_toggle_autostart)
        menu.addAction(self.autostart_act)

        reindex_act = QAction("🔄 Rebuild Application Index", self)
        reindex_act.triggered.connect(self.reindex_requested.emit)
        menu.addAction(reindex_act)

        mic_act = QAction("🎤 Test Microphone", self)
        mic_act.triggered.connect(self.mic_test_requested.emit)
        menu.addAction(mic_act)

        settings_act = QAction("⚙️ Settings", self)
        settings_act.triggered.connect(self.settings_requested.emit)
        menu.addAction(settings_act)

        menu.addSeparator()

        exit_act = QAction("🛑 Stop & Exit Drax", self)
        exit_act.triggered.connect(self.exit_requested.emit)
        menu.addAction(exit_act)

        self.setContextMenu(menu)

    def _show_pairing_code(self):
        code = cloud_connector.pairing_code
        self.notify("Drax Device Pairing", f"Your Pairing Code is: {code}\nEnter this on your Web Dashboard to connect.")

    def _on_toggle_autostart(self):
        new_state = self.autostart_act.isChecked()
        set_autostart(new_state)
        status_msg = "enabled" if new_state else "disabled"
        self.notify("Windows Startup", f"Start with Windows has been {status_msg}.")

    def _on_toggle_listen(self):
        self.is_listening_active = not self.is_listening_active
        if self.is_listening_active:
            self.listen_act.setText("🔇 Pause Wake Listening")
            self.setToolTip("DRAX AI — Active in Background")
        else:
            self.listen_act.setText("🟢 Resume Wake Listening")
            self.setToolTip("DRAX AI — Wake Listening Paused")
        self.toggle_listening_requested.emit()

    def _on_activated(self, reason):
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self.toggle_window_requested.emit()

    def notify(self, title: str, message: str):
        """Show system tray notification toast."""
        self.showMessage(title, message, QSystemTrayIcon.Information, 3000)
