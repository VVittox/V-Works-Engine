from __future__ import annotations
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPushButton, QVBoxLayout
from PySide6.QtCore import Qt
from engine.core.project_config import ProjectConfig

class InputMapDialog(QDialog):

    def __init__(self, config: ProjectConfig, parent=None) -> None:
        super().__init__(parent)
        self.config = config
        self.setWindowTitle('Input Map')
        self.resize(700, 480)
        outer = QVBoxLayout(self)
        outer.addWidget(QLabel('Godot-style input actions. Keys use pygame names: a, space, left, return, escape, left shift…'))
        self.list = QListWidget()
        outer.addWidget(self.list, 1)
        row = QHBoxLayout()
        for text, slot in [('+ Action', self.add_action), ('Edit Keys', self.edit_keys), ('Remove', self.remove_action)]:
            b = QPushButton(text)
            b.clicked.connect(slot)
            row.addWidget(b)
        row.addStretch(1)
        outer.addLayout(row)
        buttons = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Save)
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)
        self._reload()

    def _reload(self):
        self.list.clear()
        for name in sorted(self.config.input_map):
            item = QListWidgetItem(f"{name}    →    {', '.join(self.config.input_map[name])}")
            item.setData(Qt.UserRole, name)
            self.list.addItem(item)

    def add_action(self):
        name, ok = QInputDialog.getText(self, 'New Input Action', 'Action name')
        name = name.strip()
        if ok and name:
            self.config.input_map.setdefault(name, [])
            self._reload()

    def edit_keys(self):
        item = self.list.currentItem()
        if not item:
            return
        name = item.data(Qt.UserRole)
        current = ', '.join(self.config.input_map.get(name, []))
        text, ok = QInputDialog.getText(self, 'Edit Input Keys', f'Keys for {name} (comma-separated)', QLineEdit.Normal, current)
        if ok:
            self.config.input_map[name] = [x.strip().lower() for x in text.split(',') if x.strip()]
            self._reload()

    def remove_action(self):
        item = self.list.currentItem()
        if item:
            self.config.input_map.pop(item.data(Qt.UserRole), None)
            self._reload()

    def save(self):
        if 'ui_cancel' not in self.config.input_map:
            answer = QMessageBox.question(self, 'Input Map', 'ui_cancel is missing. Save anyway?', QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if answer != QMessageBox.Yes:
                return
        self.config.save()
        self.accept()
