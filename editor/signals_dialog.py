from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout

class SignalsDialog(QDialog):

    def __init__(self, root, source, parent=None):
        super().__init__(parent)
        self.root = root
        self.source = source
        self.setWindowTitle(f'Signals — {source.name}')
        self.resize(760, 520)
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel('Connect a signal from the selected node to a method on another node/script.'))
        form = QFormLayout()
        self.signal = QComboBox()
        self.signal.addItems(sorted(source.signals.names))
        self.target = QComboBox()
        self.nodes = list(root.walk())
        [self.target.addItem(n.path, n) for n in self.nodes]
        self.method = QLineEdit('on_signal')
        form.addRow('Signal', self.signal)
        form.addRow('Target', self.target)
        form.addRow('Method', self.method)
        lay.addLayout(form)
        row = QHBoxLayout()
        add = QPushButton('+ Connect')
        add.clicked.connect(self._add)
        remove = QPushButton('Disconnect Selected')
        remove.clicked.connect(self._remove)
        row.addWidget(add)
        row.addWidget(remove)
        row.addStretch()
        lay.addLayout(row)
        self.list = QListWidget()
        lay.addWidget(self.list, 1)
        self._refresh()
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.accept)
        lay.addWidget(buttons)

    def _refresh(self):
        self.list.clear()
        for c in self.source.signal_connections:
            item = QListWidgetItem(f"{c.get('signal', '')}  →  {c.get('target', '')} :: {c.get('method', '')}")
            item.setData(Qt.UserRole, c)
            self.list.addItem(item)

    def _add(self):
        if not self.signal.currentText() or not self.method.text().strip():
            return
        c = {'signal': self.signal.currentText(), 'target': self.target.currentText(), 'method': self.method.text().strip()}
        if c not in self.source.signal_connections:
            self.source.signal_connections.append(c)
            self._refresh()

    def _remove(self):
        item = self.list.currentItem()
        if item:
            c = item.data(Qt.UserRole)
            if c in self.source.signal_connections:
                self.source.signal_connections.remove(c)
            self._refresh()
