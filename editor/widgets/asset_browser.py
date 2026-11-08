from __future__ import annotations
from pathlib import Path
from PySide6.QtCore import QMimeData, QSize, Qt, QUrl, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QListView, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout, QWidget
IMAGE_EXTS = {'.png', '.jpg', '.jpeg', '.bmp', '.webp', '.gif'}
ASSET_EXTS = IMAGE_EXTS | {'.wav', '.ogg', '.mp3', '.flac', '.ttf', '.otf', '.json', '.txt', '.py', '.vscene', '.vprefab', '.vmat', '.vshader', '.vtileset', '.vres'}

class AssetListWidget(QListWidget):

    def mimeData(self, items):
        mime = QMimeData()
        urls = []
        for item in items:
            path = item.data(Qt.UserRole)
            if path:
                urls.append(QUrl.fromLocalFile(str(path)))
        mime.setUrls(urls)
        return mime

    def supportedDropActions(self):
        return Qt.DropAction.CopyAction

class AssetBrowserWidget(QWidget):
    asset_activated = Signal(str)

    def __init__(self, project_dir: str | Path, parent=None) -> None:
        super().__init__(parent)
        self.project_dir = Path(project_dir).resolve()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(4, 4, 4, 4)
        outer.setSpacing(4)
        top = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText('Search assets…')
        refresh = QPushButton('Refresh')
        top.addWidget(self.search, 1)
        top.addWidget(refresh)
        outer.addLayout(top)
        self.list = AssetListWidget()
        self.list.setViewMode(QListView.ViewMode.IconMode)
        self.list.setIconSize(QSize(64, 64))
        self.list.setGridSize(QSize(112, 98))
        self.list.setResizeMode(QListView.ResizeMode.Adjust)
        self.list.setMovement(QListView.Movement.Static)
        self.list.setWordWrap(True)
        self.list.setDragEnabled(True)
        outer.addWidget(self.list, 1)
        self.search.textChanged.connect(self.refresh)
        refresh.clicked.connect(self.refresh)
        self.list.itemDoubleClicked.connect(self._activated)
        self.refresh()

    def _iter_assets(self):
        roots = [self.project_dir / 'assets', self.project_dir / 'scenes', self.project_dir / 'scripts']
        for root in roots:
            if not root.exists():
                continue
            for path in sorted(root.rglob('*')):
                if path.is_file() and path.suffix.lower() in ASSET_EXTS:
                    yield path

    def refresh(self) -> None:
        query = self.search.text().strip().lower()
        self.list.clear()
        for path in self._iter_assets():
            rel = path.relative_to(self.project_dir).as_posix()
            if query and query not in rel.lower():
                continue
            item = QListWidgetItem(path.name)
            item.setToolTip(rel)
            item.setData(Qt.UserRole, str(path.resolve()))
            if path.suffix.lower() in IMAGE_EXTS:
                item.setIcon(QIcon(str(path)))
            elif path.suffix.lower() == '.vscene':
                item.setText('🎬 ' + path.name)
            elif path.suffix.lower() == '.vprefab':
                item.setText('🧩 ' + path.name)
            elif path.suffix.lower() == '.py':
                item.setText('🐍 ' + path.name)
            elif path.suffix.lower() == '.vmat':
                item.setText('🎨 ' + path.name)
            elif path.suffix.lower() == '.vshader':
                item.setText('✨ ' + path.name)
            elif path.suffix.lower() == '.vtileset':
                item.setText('🧱 ' + path.name)
            elif path.suffix.lower() in {'.wav', '.ogg', '.mp3', '.flac'}:
                item.setText('🔊 ' + path.name)
            self.list.addItem(item)

    def _activated(self, item: QListWidgetItem) -> None:
        path = item.data(Qt.UserRole)
        if path:
            self.asset_activated.emit(str(path))
