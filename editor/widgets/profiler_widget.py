from __future__ import annotations
from collections import deque
from PySide6.QtWidgets import QLabel, QPlainTextEdit, QVBoxLayout, QWidget

class ProfilerWidget(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.history = deque(maxlen=180)
        lay = QVBoxLayout(self)
        self.summary = QLabel('Profiler idle')
        self.summary.setStyleSheet('font-weight:700')
        lay.addWidget(self.summary)
        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)
        lay.addWidget(self.text, 1)

    def update_stats(self, stats: dict):
        self.history.append(dict(stats))
        fps = stats.get('fps', 0)
        self.summary.setText(f"Game View: {fps:.1f} FPS | Frame {stats.get('frame_ms', 0):.2f} ms | Process {stats.get('process_ms', 0):.2f} ms | Physics {stats.get('physics_ms', 0):.2f} ms | Paint {stats.get('paint_ms', 0):.2f} ms")
        self.text.setPlainText('\n'.join((f'{k:18s}: {v:.3f}' if isinstance(v, (int, float)) else f'{k}: {v}' for k, v in stats.items())))
