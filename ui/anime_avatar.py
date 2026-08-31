"""
anime_avatar.py — Futuristic Cybernetic Virtual Assistant Avatar Widget.
Renders an animated glowing holographic HUD core with rotating rings, pulsing audio waveform bars,
ambient particle effects, and dynamic state-reactive cyber-eyes/expressions.
"""

import math
import random
from PyQt5.QtCore import QPointF, QRectF, QTimer, Qt
from PyQt5.QtGui import QBrush, QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen, QRadialGradient
from PyQt5.QtWidgets import QWidget

from backend.core.logger import get_logger

logger = get_logger(__name__)


class DraxAvatarWidget(QWidget):
    """Futuristic Cybernetic Avatar Widget with multi-state animations."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(260, 260)

        self.state = "IDLE"  # IDLE, LISTENING, THINKING, SPEAKING, EXECUTING, ERROR, CONFIRMATION
        self.angle_ring1 = 0.0
        self.angle_ring2 = 0.0
        self.pulse = 0.0
        self.pulse_dir = 1
        self.eye_blink = 0.0
        self.eye_blink_timer = 0

        # Equalizer bars
        self.bar_count = 18
        self.bar_heights = [10.0] * self.bar_count
        self.target_heights = [10.0] * self.bar_count

        # Particles
        self.particles = []
        for _ in range(25):
            self.particles.append({
                "x": random.uniform(-100, 100),
                "y": random.uniform(-100, 100),
                "speed": random.uniform(0.3, 1.2),
                "size": random.uniform(1.5, 3.5),
                "alpha": random.randint(50, 180),
            })

        # 60 FPS animation timer
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._animate_frame)
        self.anim_timer.start(16)  # ~60 FPS

    def set_state(self, new_state: str):
        self.state = new_state.upper()
        self.update()

    def _animate_frame(self):
        # Ring rotations
        speed_mult = 2.5 if self.state in ["THINKING", "EXECUTING"] else (1.8 if self.state == "SPEAKING" else 1.0)
        self.angle_ring1 = (self.angle_ring1 + 1.2 * speed_mult) % 360
        self.angle_ring2 = (self.angle_ring2 - 0.8 * speed_mult) % 360

        # Core breathing pulse
        self.pulse += 0.03 * self.pulse_dir
        if self.pulse > 1.0:
            self.pulse = 1.0
            self.pulse_dir = -1
        elif self.pulse < 0.0:
            self.pulse = 0.0
            self.pulse_dir = 1

        # Eye blink logic
        self.eye_blink_timer += 1
        if self.eye_blink_timer > 180:  # Every ~3 seconds
            self.eye_blink = min(1.0, self.eye_blink + 0.2)
            if self.eye_blink >= 1.0:
                self.eye_blink_timer = 0
                self.eye_blink = 0.0

        # Update Equalizer Bars based on State
        for i in range(self.bar_count):
            if self.state in ["SPEAKING", "LISTENING"]:
                self.target_heights[i] = random.randint(12, 48)
            elif self.state in ["THINKING", "EXECUTING"]:
                self.target_heights[i] = 18 + math.sin(self.angle_ring1 * 0.05 + i * 0.4) * 12
            else:
                self.target_heights[i] = 6 + math.sin(self.pulse * math.pi + i * 0.3) * 5

            self.bar_heights[i] += (self.target_heights[i] - self.bar_heights[i]) * 0.25

        # Update floating particles
        for p in self.particles:
            p["y"] -= p["speed"]
            if p["y"] < -120:
                p["y"] = 120
                p["x"] = random.uniform(-110, 110)

        self.update()

    def _get_theme_colors(self):
        """State-reactive cyberpunk color palette."""
        if self.state == "LISTENING":
            return QColor(0, 255, 136), QColor(0, 180, 80), "LISTENING..."
        elif self.state in ["THINKING", "PROCESSING"]:
            return QColor(180, 0, 255), QColor(120, 0, 200), "PROCESSING"
        elif self.state == "EXECUTING":
            return QColor(255, 170, 0), QColor(200, 120, 0), "EXECUTING PLAN"
        elif self.state == "SPEAKING":
            return QColor(0, 243, 255), QColor(0, 160, 230), "DRAX SPEAKING"
        elif self.state == "ERROR":
            return QColor(255, 50, 70), QColor(180, 20, 30), "SYSTEM ERROR"
        elif self.state == "CONFIRMATION":
            return QColor(255, 220, 0), QColor(200, 150, 0), "CONFIRMATION"
        else:  # IDLE
            return QColor(0, 243, 255), QColor(0, 120, 200), "DRAX ONLINE"

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        w = self.width()
        h = self.height()
        cx = w / 2.0
        cy = h / 2.0 - 10
        base_radius = min(w, h) * 0.32

        primary_color, secondary_color, label_text = self._get_theme_colors()

        # ── 1. Floating Hologram Background Particles ───────────────────────
        for p in self.particles:
            alpha = max(0, min(255, int(p["alpha"] * (0.6 + 0.4 * self.pulse))))
            p_color = QColor(primary_color)
            p_color.setAlpha(alpha)
            painter.setBrush(QBrush(p_color))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QPointF(cx + p["x"], cy + p["y"]), p["size"], p["size"])

        # ── 2. Outer Rotating Holographic Rings ─────────────────────────────
        # Outer Ring 1
        pen1 = QPen(primary_color, 2, Qt.DashLine)
        pen1.setDashPattern([8, 6, 2, 6])
        painter.setPen(pen1)
        painter.setBrush(Qt.NoBrush)
        painter.save()
        painter.translate(cx, cy)
        painter.rotate(self.angle_ring1)
        r1 = base_radius + 24
        painter.drawEllipse(QRectF(-r1, -r1, r1 * 2, r1 * 2))
        painter.restore()

        # Inner Ring 2
        pen2 = QPen(secondary_color, 1.5, Qt.DotLine)
        painter.setPen(pen2)
        painter.save()
        painter.translate(cx, cy)
        painter.rotate(self.angle_ring2)
        r2 = base_radius + 12
        painter.drawEllipse(QRectF(-r2, -r2, r2 * 2, r2 * 2))
        painter.restore()

        # ── 3. Central Radial Glowing Orb Core ──────────────────────────────
        pulse_rad = base_radius + (self.pulse * 6)
        radial = QRadialGradient(cx, cy, pulse_rad)
        c_glow = QColor(primary_color)
        c_glow.setAlpha(max(0, min(255, int(160 + 60 * self.pulse))))
        radial.setColorAt(0.0, c_glow)
        radial.setColorAt(0.5, QColor(8, 15, 28, 220))
        radial.setColorAt(1.0, QColor(4, 7, 12, 0))

        painter.setPen(QPen(primary_color, 2))
        painter.setBrush(QBrush(radial))
        painter.drawEllipse(QPointF(cx, cy), pulse_rad, pulse_rad)

        # ── 4. Stylized Cybernetic Avatar Eyes ─────────────────────────────
        eye_spacing = 22
        eye_y = cy - 6
        eye_h = max(2, int(14 * (1.0 - self.eye_blink)))
        eye_w = 12

        painter.setBrush(QBrush(primary_color))
        painter.setPen(QPen(QColor(255, 255, 255), 1.5))

        # Left Cyber Eye
        left_eye_rect = QRectF(cx - eye_spacing - eye_w / 2, eye_y - eye_h / 2, eye_w, eye_h)
        painter.drawRoundedRect(left_eye_rect, 4, 4)

        # Right Cyber Eye
        right_eye_rect = QRectF(cx + eye_spacing - eye_w / 2, eye_y - eye_h / 2, eye_w, eye_h)
        painter.drawRoundedRect(right_eye_rect, 4, 4)

        # ── 5. Lower Equalizer Soundwave HUD ────────────────────────────────
        bar_w = 4
        bar_gap = 4
        total_eq_w = self.bar_count * (bar_w + bar_gap)
        start_x = cx - total_eq_w / 2.0
        eq_base_y = cy + base_radius - 12

        for i, bh in enumerate(self.bar_heights):
            bx = start_x + i * (bar_w + bar_gap)
            grad = QLinearGradient(bx, eq_base_y - bh, bx, eq_base_y)
            grad.setColorAt(0.0, primary_color)
            grad.setColorAt(1.0, secondary_color)

            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(grad))
            painter.drawRoundedRect(QRectF(bx, eq_base_y - bh, bar_w, bh), 2, 2)

        # ── 6. State Label HUD Display ──────────────────────────────────────
        painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
        painter.setPen(QPen(primary_color))
        label_rect = QRectF(cx - 90, h - 30, 180, 20)
        painter.drawText(label_rect, Qt.AlignCenter, f"◈ {label_text} ◈")

        painter.end()
