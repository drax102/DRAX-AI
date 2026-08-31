# Futuristic Cybernetic UI Style Sheet for DRAX AI

CYBER_STYLE = """
QMainWindow {
    background-color: #080B10;
}

QWidget#CentralWidget {
    background-color: #080B10;
}

/* Header Container */
QFrame#HeaderFrame {
    background-color: #0F172A;
    border: 1px solid #1E293B;
    border-radius: 12px;
    margin-bottom: 6px;
}

QLabel#TitleLabel {
    color: #00F3FF;
    font-size: 20px;
    font-weight: bold;
    font-family: 'Segoe UI', 'Consolas', sans-serif;
    letter-spacing: 2px;
}

QLabel#SubtitleLabel {
    color: #94A3B8;
    font-size: 11px;
    font-family: 'Consolas', sans-serif;
}

QLabel#StatLabel {
    color: #00FF99;
    font-size: 12px;
    font-weight: bold;
    font-family: 'Consolas', monospace;
    background: #080B10;
    border: 1px solid #00F3FF;
    border-radius: 6px;
    padding: 4px 8px;
}

/* Chat Terminal Window */
QTextEdit#ChatTerminal {
    background-color: #0D131F;
    color: #E2E8F0;
    border: 1px solid #1E293B;
    border-radius: 12px;
    padding: 12px;
    font-family: 'Consolas', 'Segoe UI', monospace;
    font-size: 14px;
    selection-background-color: #00F3FF;
    selection-color: #080B10;
}

/* Scrollbars */
QScrollBar:vertical {
    background: #0D131F;
    width: 8px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: #00F3FF;
    border-radius: 4px;
    min-height: 20px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

/* Futuristic Action Buttons */
QPushButton {
    background-color: #0F172A;
    color: #00F3FF;
    border: 1px solid #00F3FF;
    border-radius: 8px;
    padding: 8px 14px;
    font-size: 13px;
    font-weight: bold;
    font-family: 'Segoe UI', sans-serif;
}

QPushButton:hover {
    background-color: #00F3FF;
    color: #080B10;
    border: 1px solid #00F3FF;
}

QPushButton:pressed {
    background-color: #00B8C4;
    color: #080B10;
}

/* Voice Mic Button */
QPushButton#MicBtn {
    background-color: #080B10;
    color: #00FF99;
    border: 2px solid #00FF99;
    border-radius: 10px;
    font-size: 14px;
    font-weight: bold;
    padding: 8px 16px;
}

QPushButton#MicBtn:hover {
    background-color: #00FF99;
    color: #080B10;
}

/* Command Input Field */
QLineEdit#CommandInput {
    background-color: #0F172A;
    color: #00F3FF;
    border: 1.5px solid #1E293B;
    border-radius: 10px;
    padding: 10px 14px;
    font-size: 14px;
    font-family: 'Consolas', 'Segoe UI', monospace;
}

QLineEdit#CommandInput:focus {
    border: 1.5px solid #00F3FF;
    background-color: #131D33;
}
"""
