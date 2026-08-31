import math
import random
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QRadialGradient, QLinearGradient, QFont


class DraxVisualizer(QWidget):
    """
    Custom futuristic HUD visualizer widget for DRAX AI.
    Renders animated glowing reactor rings, rotating orbits, dynamic energy pulses,
    and reactive audio spectrum equalizer bars.
    """
    STATE_IDLE = "IDLE"
    STATE_LISTENING = "LISTENING"
    STATE_PROCESSING = "PROCESSING"
    STATE_SPEAKING = "SPEAKING"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(220, 220)
        self.state = self.STATE_IDLE

        # Animation state variables
        self.angle_outer = 0.0
        self.angle_inner = 0.0
        self.pulse_phase = 0.0
        self.bar_heights = [15.0] * 16

        # Timer for smooth 60 FPS animation loop
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_animation)
        self.timer.start(16)  # ~60 FPS

    def set_state(self, new_state: str):
        self.state = new_state
        self.update()

    def update_animation(self):
        # Rotation angles
        self.angle_outer = (self.angle_outer + (1.2 if self.state == self.STATE_PROCESSING else 0.5)) % 360
        self.angle_inner = (self.angle_inner - (2.0 if self.state == self.STATE_PROCESSING else 0.8)) % 360
        self.pulse_phase = (self.pulse_phase + 0.05) % (2 * math.pi)

        # Equalizer audio bar simulation
        if self.state in [self.STATE_SPEAKING, self.STATE_LISTENING]:
            for i in range(len(self.bar_heights)):
                target = float(random.randint(10, 55 if self.state == self.STATE_SPEAKING else 35))
                self.bar_heights[i] += (target - self.bar_heights[i]) * 0.25
        else:
            for i in range(len(self.bar_heights)):
                self.bar_heights[i] += (12.0 - self.bar_heights[i]) * 0.15

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        width = self.width()
        height = self.height()
        cx = width / 2.0
        cy = height / 2.0
        radius = min(cx, cy) - 15.0

        # Colors based on state
        if self.state == self.STATE_LISTENING:
            primary_color = QColor(0, 255, 170)   # Neon Emerald/Green
            glow_color = QColor(0, 255, 170, 80)
        elif self.state == self.STATE_PROCESSING:
            primary_color = QColor(255, 170, 0)   # Cyber Amber/Gold
            glow_color = QColor(255, 170, 0, 80)
        elif self.state == self.STATE_SPEAKING:
            primary_color = QColor(0, 243, 255)   # Electric Cyan
            glow_color = QColor(0, 243, 255, 110)
        else:  # IDLE
            primary_color = QColor(0, 180, 255)   # Deep Cyber Blue
            glow_color = QColor(0, 180, 255, 50)

        # 1. Background Radial Glow Core
        pulse_scale = 1.0 + 0.06 * math.sin(self.pulse_phase)
        core_radius = radius * 0.45 * pulse_scale

        radial_grad = QRadialGradient(cx, cy, max(1.0, core_radius))
        radial_grad.setColorAt(0.0, primary_color)
        radial_grad.setColorAt(0.5, glow_color)
        radial_grad.setColorAt(1.0, QColor(8, 11, 16, 0))
        painter.setBrush(QBrush(radial_grad))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QPointF(cx, cy), core_radius, core_radius)

        # 2. Outer Rotating HUD Arc Rings
        painter.save()
        painter.translate(cx, cy)

        # Outer segmented ring
        painter.rotate(self.angle_outer)
        pen_outer = QPen(primary_color, 2.5)
        pen_outer.setCapStyle(Qt.RoundCap)
        painter.setPen(pen_outer)

        arc_rect = QRectF(-radius, -radius, radius * 2, radius * 2)
        for i in range(4):
            painter.drawArc(arc_rect, int(i * 90 * 16 + 10 * 16), int(60 * 16))

        # Inner dashed ring
        painter.rotate(self.angle_inner - self.angle_outer)
        pen_inner = QPen(QColor(primary_color.red(), primary_color.green(), primary_color.blue(), 140), 1.5)
        pen_inner.setStyle(Qt.DashLine)
        painter.setPen(pen_inner)
        inner_rect = QRectF(-radius * 0.75, -radius * 0.75, radius * 1.5, radius * 1.5)
        painter.drawEllipse(inner_rect)

        painter.restore()

        # 3. Audio Spectrum Equalizer Bars
        bar_count = len(self.bar_heights)
        bar_width = 4.0
        total_width = bar_count * (bar_width + 4)
        start_x = cx - total_width / 2.0

        for i, h in enumerate(self.bar_heights):
            x = start_x + i * (bar_width + 4)
            bar_color = QColor(primary_color)
            alpha_val = max(0, min(255, int(180 + 75 * math.sin(self.pulse_phase + i))))
            bar_color.setAlpha(alpha_val)
            painter.setBrush(QBrush(bar_color))
            painter.setPen(Qt.NoPen)
            
            # Symmetrical bars
            painter.drawRoundedRect(QRectF(x, cy - h / 2.0, bar_width, max(2.0, h)), 2, 2)

        # 4. Central HUD State Label Text
        painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
        painter.setPen(QColor(240, 245, 255))
        state_text = f"// {self.state} //"
        painter.drawText(QRectF(cx - 80, cy + radius * 0.55, 160, 25), Qt.AlignCenter, state_text)
