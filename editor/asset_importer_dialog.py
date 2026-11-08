from __future__ import annotations
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget, QPushButton, QVBoxLayout
from .asset_importer import AssetImporter

class AssetImporterDialog(QDialog):

    def __init__(self, project_dir, parent=None):
        super().__init__(parent)
        self.project_dir = Path(project_dir).resolve()
        self.importer = AssetImporter(self.project_dir)
        self.setWindowTitle('Import Assets')
        self.resize(720, 480)
        lay = QVBoxLayout(self)
        top = QHBoxLayout()
        add = QPushButton('+ Add Files…')
        add.clicked.connect(self._add)
        clear = QPushButton('Clear')
        clear.clicked.connect(lambda: self.files.clear())
        top.addWidget(add)
        top.addWidget(clear)
        top.addStretch()
        lay.addLayout(top)
        self.files = QListWidget()
        lay.addWidget(self.files, 1)
        form = QFormLayout()
        self.sub = QLineEdit('imported')
        form.addRow('Destination inside assets/', self.sub)
        lay.addLayout(form)
        self.status = QLabel('Select any textures, audio, fonts, scenes, prefabs or resource files.')
        self.status.setWordWrap(True)
        lay.addWidget(self.status)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        self.import_btn = buttons.addButton('Import', QDialogButtonBox.AcceptRole)
        self.import_btn.clicked.connect(self._import)
        buttons.rejected.connect(self.reject)
        lay.addWidget(buttons)

    def _add(self):
        paths, _ = QFileDialog.getOpenFileNames(self, 'Import Assets', str(Path.home()), 'All supported (*.*)')
        existing = {self.files.item(i).text() for i in range(self.files.count())}
        for p in paths:
            if p not in existing:
                self.files.addItem(p)

    def _import(self):
        paths = [self.files.item(i).text() for i in range(self.files.count())]
        if not paths:
            return
        imported = self.importer.import_many(paths, self.sub.text().strip().replace('\\', '/').strip('/'))
        self.status.setText(f'Imported {len(imported)} asset(s). Metadata written to .vworks/imports/')
        self.files.clear()
        self.accept()
