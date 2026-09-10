from __future__ import annotations
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QAbstractItemView, QDialog, QDialogButtonBox, QFileDialog, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QMessageBox, QPushButton, QVBoxLayout
from engine.core.project_config import BuildScene, ProjectConfig

class BuildScenesDialog(QDialog):

    def __init__(self, config: ProjectConfig, current_scene: Path | None=None, parent=None) -> None:
        super().__init__(parent)
        self.config = config
        self.current_scene = current_scene
        self.setWindowTitle('Build Scenes')
        self.resize(760, 520)
        outer = QVBoxLayout(self)
        help_text = QLabel('Scenes are loaded by index in this order. Checked scenes are included in the playable build list. The startup scene is marked ★.')
        help_text.setWordWrap(True)
        outer.addWidget(help_text)
        self.list = QListWidget()
        self.list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.list.setDefaultDropAction(Qt.DropAction.MoveAction)
        outer.addWidget(self.list, 1)
        self.list.model().rowsMoved.connect(lambda *args: self._renumber())
        row = QHBoxLayout()
        for text, slot in [('Add Open Scene', self.add_open_scene), ('Add Scenes…', self.add_scenes), ('Add All Project Scenes', self.add_all), ('Remove', self.remove), ('Move Up', lambda: self.move(-1)), ('Move Down', lambda: self.move(1)), ('Set Startup', self.set_startup)]:
            btn = QPushButton(text)
            btn.clicked.connect(slot)
            row.addWidget(btn)
        outer.addLayout(row)
        buttons = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Save)
        buttons.accepted.connect(self._save_and_accept)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)
        self._load()

    def _label(self, path: str, index: int) -> str:
        star = '★ ' if path == self.config.main_scene else ''
        return f'{index:02d}   {star}{path}'

    def _load(self) -> None:
        self.list.clear()
        self.config.ensure_build_scenes()
        for i, scene in enumerate(self.config.build.scenes):
            item = QListWidgetItem(self._label(scene.path, i))
            item.setData(Qt.UserRole, scene.path)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsDragEnabled)
            item.setCheckState(Qt.Checked if scene.enabled else Qt.Unchecked)
            self.list.addItem(item)

    def _paths(self) -> list[str]:
        return [str(self.list.item(i).data(Qt.UserRole)) for i in range(self.list.count())]

    def _relative(self, path: str | Path) -> str | None:
        try:
            return Path(path).resolve().relative_to(self.config.root).as_posix()
        except ValueError:
            QMessageBox.warning(self, 'Build Scenes', 'Scenes must be inside the project folder.')
            return None

    def _append(self, rel: str) -> None:
        if rel in self._paths():
            self.list.setCurrentRow(self._paths().index(rel))
            return
        item = QListWidgetItem(rel)
        item.setData(Qt.UserRole, rel)
        item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsDragEnabled)
        item.setCheckState(Qt.Checked)
        self.list.addItem(item)
        self.list.setCurrentItem(item)
        self._renumber()

    def add_open_scene(self) -> None:
        if self.current_scene and self.current_scene.exists():
            rel = self._relative(self.current_scene)
            if rel:
                self._append(rel)

    def add_scenes(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(self, 'Add Build Scenes', str(self.config.root / 'scenes'), 'V Works Scenes (*.vscene)')
        for path in paths:
            rel = self._relative(path)
            if rel:
                self._append(rel)

    def add_all(self) -> None:
        for path in sorted(self.config.root.rglob('*.vscene')):
            if any((part in {'builds', '.vworks', '.venv'} for part in path.parts)):
                continue
            rel = self._relative(path)
            if rel:
                self._append(rel)

    def remove(self) -> None:
        row = self.list.currentRow()
        if row >= 0:
            self.list.takeItem(row)
            self._renumber()

    def move(self, delta: int) -> None:
        row = self.list.currentRow()
        target = row + delta
        if row < 0 or target < 0 or target >= self.list.count():
            return
        item = self.list.takeItem(row)
        self.list.insertItem(target, item)
        self.list.setCurrentRow(target)
        self._renumber()

    def set_startup(self) -> None:
        item = self.list.currentItem()
        if item is None:
            return
        self.config.main_scene = str(item.data(Qt.UserRole))
        item.setCheckState(Qt.Checked)
        self._renumber()

    def _renumber(self) -> None:
        for i in range(self.list.count()):
            item = self.list.item(i)
            item.setText(self._label(str(item.data(Qt.UserRole)), i))

    def _save_and_accept(self) -> None:
        scenes: list[BuildScene] = []
        for i in range(self.list.count()):
            item = self.list.item(i)
            path = str(item.data(Qt.UserRole))
            scenes.append(BuildScene(path, item.checkState() == Qt.Checked))
        if not scenes:
            QMessageBox.warning(self, 'Build Scenes', 'Add at least one scene before saving.')
            return
        if not any((s.enabled for s in scenes)):
            QMessageBox.warning(self, 'Build Scenes', 'At least one build scene must be enabled.')
            return
        startup = next((s for s in scenes if s.path == self.config.main_scene), None)
        if startup is not None and (not startup.enabled):
            startup.enabled = True
        self.config.build.scenes = scenes
        if self.config.main_scene not in [s.path for s in scenes]:
            self.config.main_scene = next((s.path for s in scenes if s.enabled))
        self.config.save()
        self.accept()
