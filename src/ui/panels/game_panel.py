"""Game panel with status summary and log stream."""

from __future__ import annotations

from src.ui.qt import QFont, QLabel, QTextEdit, QVBoxLayout, QWidget
from src.ui.utils import format_timestamp


class GamePanel(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)

        self.mode_label = QLabel("Mode: Vision Only")
        self.side_label = QLabel("Side to move: White")
        self.last_move_label = QLabel("Last move: -")
        self.suggested_label = QLabel("Suggested move: -")
        self.fen_label = QLabel("FEN: -")
        for label in [self.mode_label, self.side_label, self.last_move_label, self.suggested_label, self.fen_label]:
            label.setFont(QFont("Helvetica", 10))
            layout.addWidget(label)

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setStyleSheet("background: #111; color: #ddd;")
        layout.addWidget(self.log_view)

    def update_status(self, status) -> None:
        self.mode_label.setText(f"Mode: {status.mode}")
        self.side_label.setText(f"Side to move: {status.side_to_move}")
        self.last_move_label.setText(f"Last move: {status.last_detected_move}")
        self.suggested_label.setText(f"Suggested move: {status.suggested_move}")
        self.fen_label.setText(f"FEN: {status.fen}")

    def append_log(self, event) -> None:
        timestamp = format_timestamp(event.timestamp)
        self.log_view.append(f"[{timestamp}] [{event.category}] {event.message}")
