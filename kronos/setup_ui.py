"""Native Qt credential setup. QPainter artwork; no browser or web view."""
from __future__ import annotations

import math
import sys
from pathlib import Path

from PyQt6.QtCore import QPointF, QRectF, Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPalette, QPen, QRadialGradient
from PyQt6.QtWidgets import (
    QApplication, QDialog, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QVBoxLayout, QWidget,
)

from .credentials import SetupError, save_connection
from .providers import Config, ProviderError, default_model


PROVIDER_LABELS = {"groq": "Groq", "openrouter": "OpenRouter", "nvidia": "NVIDIA"}
MODEL_NOTES = {
    "groq": "KRONOS will use Groq's strongest hosted tool-capable default.",
    "openrouter": "KRONOS will let OpenRouter auto-route to the best model for each request.",
    "nvidia": "KRONOS will use NVIDIA's Llama 3.3 70B tool-capable default.",
}


def font(size: int, weight=QFont.Weight.Normal, tracking: float = 0) -> QFont:
    result = QFont("Segoe UI" if sys.platform == "win32" else "Helvetica Neue", size, weight)
    if tracking:
        result.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, tracking)
    return result


def label(text: str, size: int, color: str = "#F2F0F9", weight=QFont.Weight.Normal) -> QLabel:
    widget = QLabel(text)
    widget.setFont(font(size, weight))
    widget.setStyleSheet(f"color: {color}; background: transparent;")
    widget.setWordWrap(True)
    return widget


class Identity(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumWidth(310)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(34, 34, 28, 30)
        brand = label("K  /  K R O N O S", 13, "#DED9F0", QFont.Weight.DemiBold)
        layout.addWidget(brand)
        layout.addStretch(1)
        layout.addWidget(label("A mind.\nAt your service.", 31, weight=QFont.Weight.DemiBold))
        caption = label("Your world. Your rhythm.\nYour personal butler.", 11, "#B3AEC5")
        layout.addSpacing(8)
        layout.addWidget(caption)
        layout.addSpacing(28)
        bottom = label("P E R S O N A L   I N T E L L I G E N C E", 8, "#A49ABF")
        layout.addWidget(bottom)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#23212E"))
        cx, cy = self.width() * .49, self.height() * .34
        glow = QRadialGradient(QPointF(cx, cy), self.width() * .62)
        glow.setColorAt(0, QColor(145, 119, 232, 55))
        glow.setColorAt(.5, QColor(104, 82, 177, 22))
        glow.setColorAt(1, QColor(30, 29, 39, 0))
        painter.fillRect(self.rect(), glow)
        for i in range(4):
            radius = 65 + i * 17
            painter.setPen(QPen(QColor(167, 149, 218, 55 - i * 9), 1))
            painter.drawEllipse(QPointF(cx, cy), radius, radius)
        for i in range(60):
            angle = i * math.tau / 60
            r1, r2 = (126, 135) if i % 5 == 0 else (130, 133)
            painter.setPen(QPen(QColor(197, 180, 237, 95 if i % 5 == 0 else 40), 1))
            painter.drawLine(QPointF(cx + math.cos(angle) * r1, cy + math.sin(angle) * r1),
                             QPointF(cx + math.cos(angle) * r2, cy + math.sin(angle) * r2))
        gradient = QLinearGradient(cx - 60, cy - 60, cx + 50, cy + 70)
        gradient.setColorAt(0, QColor("#E3D8FF"))
        gradient.setColorAt(.55, QColor("#9F89DD"))
        gradient.setColorAt(1, QColor("#685688"))
        painter.setBrush(gradient)
        painter.setPen(Qt.PenStyle.NoPen)
        # Sculpted K, drawn as geometry rather than a font or bitmap.
        for points in (
            [(-34, -48), (-18, -48), (-18, 48), (-34, 48)],
            [(-10, -4), (23, -48), (45, -48), (8, 0), (45, 48), (23, 48), (-10, 6)],
        ):
            path = QPainterPath()
            path.moveTo(cx + points[0][0], cy + points[0][1])
            for x, y in points[1:]:
                path.lineTo(cx + x, cy + y)
            path.closeSubpath()
            painter.drawPath(path)
        painter.setPen(QPen(QColor("#CAB5FF"), 2))
        painter.drawArc(QRectF(cx - 101, cy - 101, 202, 202), 30 * 16, 65 * 16)
        painter.setPen(QPen(QColor("#8B739E"), 2))
        painter.drawArc(QRectF(cx - 101, cy - 101, 202, 202), 208 * 16, 35 * 16)


class SaveWorker(QThread):
    completed = pyqtSignal(bool, str)

    def __init__(self, path, provider, model, key, parent=None):
        super().__init__(parent)
        self.path, self.provider, self.model, self.key = path, provider, model, key

    def run(self):
        try:
            save_connection(self.path, self.provider, self.model, self.key)
        except SetupError as exc:
            self.completed.emit(False, str(exc))
        except Exception:
            self.completed.emit(False, "Connection could not be saved. Please try again.")
        else:
            self.completed.emit(True, "Connection saved to your OS credential store. Provider access has not been tested yet.")
        finally:
            self.key = ""


class SetupDialog(QDialog):
    def __init__(self, path: Path):
        super().__init__()
        self.path, self.provider = path, "groq"
        self.worker = None
        self.saved = False
        self.pending_result = None
        self.setWindowTitle("KRONOS · Connection setup")
        self.resize(920, 650)
        self.setMinimumSize(820, 650)
        self.setObjectName("SetupDialog")
        self.setStyleSheet("""
            QDialog#SetupDialog { background: #1D1E25; }
            QLineEdit { background: #282932; color: #F1EEF9; border: 1px solid #41414F;
                border-radius: 10px; padding: 12px 14px; selection-background-color: #78639E; }
            QLineEdit:focus { border: 1px solid #B9A0F0; background: #2C2B37; }
            QPushButton { color: #C0BDCD; border: 1px solid #40404C; background: #25262E;
                border-radius: 9px; padding: 11px 12px; }
            QPushButton:hover { background: #32303D; border-color: #8C7BB2; color: #F4F0FF; }
            QPushButton:checked { background: #3B324E; border-color: #B7A0E4; color: #EFE6FF; }
            QPushButton:disabled { color: #817A91; }
            QPushButton#Primary { background: #C8B2F4; color: #211A30; border: none;
                border-radius: 11px; padding: 15px; font-weight: 600; }
            QPushButton#Primary:hover { background: #D7C5FB; }
            QPushButton#Primary:disabled { background: #655776; color: #D5CADF; }
            QPushButton#Utility { border: none; background: transparent; color: #C7B3E8; padding: 6px; }
        """)
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(Identity(), 4)
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(38, 32, 38, 28)
        layout.setSpacing(0)
        outer.addWidget(panel, 6)
        top = QHBoxLayout()
        top.addWidget(label("CONNECTION SETUP", 9, "#B6A8D1", QFont.Weight.DemiBold))
        top.addStretch()
        top.addWidget(label("01 / 01", 9, "#8F8B9D"))
        layout.addLayout(top)
        layout.addSpacing(23)
        layout.addWidget(label("Bring KRONOS online.", 26, weight=QFont.Weight.DemiBold))
        layout.addSpacing(7)
        layout.addWidget(label("Choose the provider. Add your key.\nKRONOS picks the model.", 11, "#AAA6B8"))
        layout.addSpacing(26)
        layout.addWidget(label("PROVIDER", 9, "#AAA6B8", QFont.Weight.DemiBold))
        layout.addSpacing(9)
        providers = QHBoxLayout()
        providers.setSpacing(8)
        self.provider_buttons = {}
        for provider, title in PROVIDER_LABELS.items():
            button = QPushButton(title)
            button.setCheckable(True)
            button.setFont(font(10, QFont.Weight.DemiBold))
            button.clicked.connect(lambda checked, selected=provider: self.select_provider(selected))
            self.provider_buttons[provider] = button
            providers.addWidget(button)
        layout.addLayout(providers)
        layout.addSpacing(22)
        layout.addWidget(label("MODEL", 9, "#AAA6B8", QFont.Weight.DemiBold))
        layout.addSpacing(8)
        self.model = QLineEdit()
        self.model.setFont(font(11))
        self.model.setAccessibleName("Selected model")
        self.model.setMinimumHeight(47)
        self.model.setReadOnly(True)
        layout.addWidget(self.model)
        layout.addSpacing(7)
        self.model_note = label("", 10, "#A29BAC")
        layout.addWidget(self.model_note)
        layout.addSpacing(18)
        key_heading = QHBoxLayout()
        key_heading.addWidget(label("API KEY", 9, "#AAA6B8", QFont.Weight.DemiBold))
        key_heading.addStretch()
        self.reveal = QPushButton("Show")
        self.reveal.setObjectName("Utility")
        self.reveal.setCheckable(True)
        self.reveal.setAccessibleName("Show or hide API key")
        self.reveal.clicked.connect(self.toggle_key)
        key_heading.addWidget(self.reveal)
        layout.addLayout(key_heading)
        layout.addSpacing(5)
        key_row = QHBoxLayout()
        self.key = QLineEdit()
        self.key.setFont(font(11))
        self.key.setEchoMode(QLineEdit.EchoMode.Password)
        self.key.setPlaceholderText("Paste your API key")
        self.key.setAccessibleName("API key")
        self.key.setMaxLength(4096)
        self.key.setMinimumHeight(47)
        self.paste = QPushButton("Paste")
        self.paste.setMinimumHeight(47)
        self.paste.setFont(font(10))
        self.paste.clicked.connect(self.paste_key)
        key_row.addWidget(self.key, 1)
        key_row.addWidget(self.paste)
        layout.addLayout(key_row)
        layout.addSpacing(11)
        layout.addWidget(label("Stored in your OS credential store.\nNever saved in a project file.", 10, "#A29BAC"))
        layout.addStretch()
        self.status = label("", 10, "#F2B7B7")
        self.status.setMinimumHeight(46)
        self.status.setAccessibleName("Setup status")
        layout.addWidget(self.status)
        layout.addSpacing(10)
        self.save_button = QPushButton("Save connection   →")
        self.save_button.setFont(font(12, QFont.Weight.DemiBold))
        self.save_button.setObjectName("Primary")
        self.save_button.setMinimumHeight(51)
        self.save_button.clicked.connect(self.save)
        self.save_button.setDefault(True)
        layout.addWidget(self.save_button)
        self.select_provider("groq")
        try:
            config = Config.load(path)
            self.select_provider(config.provider)
            if config.model:
                self.model.setText(config.model)
        except ProviderError:
            self.status.setText("Existing configuration needs repair. Save a new connection below.")
        self.key.setFocus()

    def select_provider(self, selected):
        changed = selected != self.provider
        self.provider = selected
        for provider, button in self.provider_buttons.items():
            button.setChecked(provider == selected)
        if changed:
            self.key.clear()
            self.reveal.setChecked(False)
            self.toggle_key(False)
        if changed or not self.model.text():
            self.model.setText(default_model(selected))
        self.model.setPlaceholderText(default_model(selected))
        self.model_note.setText(MODEL_NOTES[selected])

    def toggle_key(self, visible):
        self.key.setEchoMode(QLineEdit.EchoMode.Normal if visible else QLineEdit.EchoMode.Password)
        self.reveal.setText("Hide" if visible else "Show")

    def paste_key(self):
        self.key.setText(QApplication.clipboard().text().strip())
        self.key.setFocus()

    def save(self):
        if self.saved:
            self.accept()
            return
        if self.worker and self.worker.isRunning():
            return
        if not self.key.text().strip():
            self.status.setText("Paste an API key to continue.")
            self.key.setFocus()
            return
        self.set_busy(True)
        self.status.setStyleSheet("color: #BDB0D5;")
        self.status.setText("Saving securely… Allow OS credential access if prompted.")
        self.worker = SaveWorker(self.path, self.provider, self.model.text(), self.key.text(), self)
        self.worker.completed.connect(self.capture_result)
        self.worker.finished.connect(self.save_finished)
        self.worker.start()

    def set_busy(self, busy):
        for widget in (*self.provider_buttons.values(), self.model, self.key, self.paste, self.reveal, self.save_button):
            widget.setEnabled(not busy)
        self.save_button.setText("Saving connection…" if busy else "Save connection   →")

    def capture_result(self, ok, message):
        self.pending_result = (ok, message)

    def save_finished(self):
        ok, message = self.pending_result or (False, "Save did not finish. Please try again.")
        self.pending_result = None
        self.set_busy(False)
        self.status.setStyleSheet("color: #B8DCC7;" if ok else "color: #F2B7B7;")
        self.status.setText(message)
        if ok:
            self.saved = True
            self.key.clear()
            self.reveal.setChecked(False)
            self.toggle_key(False)
            for widget in (*self.provider_buttons.values(), self.model, self.key, self.paste, self.reveal):
                widget.setEnabled(False)
            self.save_button.setText("Continue   →")

    def reject(self):
        # Do not destroy a QThread while the OS keychain dialog is active.
        if self.worker and self.worker.isRunning():
            return
        self.key.clear()
        super().reject()

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            event.ignore()
        else:
            self.key.clear()
            super().closeEvent(event)


def run_setup(path: Path) -> int:
    app = QApplication.instance() or QApplication([])
    app.setStyle("Fusion")
    palette = app.palette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#1D1E25"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#F2F0F9"))
    app.setPalette(palette)
    dialog = SetupDialog(path)
    return 0 if dialog.exec() == QDialog.DialogCode.Accepted else 1
