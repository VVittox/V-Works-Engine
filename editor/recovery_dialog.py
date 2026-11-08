from __future__ import annotations
import json
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout

class RecoveryDialog(QDialog):

    def __init__(self, project_dir, parent=None):
        super().__init__(parent)
        self.project_dir = Path(project_dir).resolve()
        self.setWindowTitle('Autosave / Recovery')
        self.resize(760, 480)
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel('Recovery snapshots are stored in .vworks/autosave. Choose one to open as a new unsaved document.'))
        self.list = QListWidget()
        lay.addWidget(self.list, 1)
        self._load()
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        self.restore = buttons.addButton('Open Recovery', QDialogButtonBox.AcceptRole)
        self.restore.clicked.connect(self.accept)
        buttons.rejected.connect(self.reject)
        lay.addWidget(buttons)

    def _load(self):
        folder = self.project_dir / '.vworks' / 'autosave'
        for p in sorted(folder.glob('*.vscene'), key=lambda x: x.stat().st_mtime, reverse=True):
            item = QListWidgetItem(f'{p.name}    {p.stat().st_mtime:.0f}')
            item.setData(Qt.UserRole, str(p))
            self.list.addItem(item)
        if self.list.count():
            self.list.setCurrentRow(0)

    def selected_path(self):
        item = self.list.currentItem()
        return Path(item.data(Qt.UserRole)) if item else None
