from __future__ import annotations
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QCheckBox, QFormLayout, QHBoxLayout, QLabel, QPushButton, QSpinBox, QVBoxLayout, QWidget
from engine.scene import Navigation2D

class NavigationPanel(QWidget):
    changed = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.node = None
        lay = QVBoxLayout(self)
        self.title = QLabel('Select a Navigation2D')
        self.title.setStyleSheet('font-weight:700')
        lay.addWidget(self.title)
        form = QFormLayout()
        self.x = QSpinBox()
        self.x.setRange(0, 9999)
        self.y = QSpinBox()
        self.y.setRange(0, 9999)
        form.addRow('Cell X', self.x)
        form.addRow('Cell Y', self.y)
        lay.addLayout(form)
        row = QHBoxLayout()
        block = QPushButton('Block')
        block.clicked.connect(lambda: self._set(True))
        free = QPushButton('Unblock')
        free.clicked.connect(lambda: self._set(False))
        row.addWidget(block)
        row.addWidget(free)
        lay.addLayout(row)
        boundary = QPushButton('Block Boundary')
        boundary.clicked.connect(self._boundary)
        clear = QPushButton('Clear Obstacles')
        clear.clicked.connect(self._clear)
        lay.addWidget(boundary)
        lay.addWidget(clear)
        lay.addStretch(1)

    def set_node(self, node):
        self.node = node if isinstance(node, Navigation2D) else None
        self.title.setText(f'Navigation: {self.node.name} — {len(self.node.blocked)} blocked' if self.node else 'Select a Navigation2D')

    def _set(self, value):
        if self.node:
            self.node.set_blocked(self.x.value(), self.y.value(), value)
            self.set_node(self.node)
            self.changed.emit(self.node)

    def _boundary(self):
        if not self.node:
            return
        for x in range(self.node.width):
            self.node.set_blocked(x, 0)
            self.node.set_blocked(x, self.node.height - 1)
        for y in range(self.node.height):
            self.node.set_blocked(0, y)
            self.node.set_blocked(self.node.width - 1, y)
        self.set_node(self.node)
        self.changed.emit(self.node)

    def _clear(self):
        if self.node:
            self.node.blocked.clear()
            self.set_node(self.node)
            self.changed.emit(self.node)
