from __future__ import annotations
from pathlib import Path
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QCheckBox, QFileDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QSpinBox, QVBoxLayout, QWidget
from engine.scene import TileMap2D
from engine.utils.vmath import Vector2

class TileMapPanel(QWidget):
    changed = Signal(object)
    paint_settings_changed = Signal(bool, int)

    def __init__(self, project_dir, parent=None):
        super().__init__(parent)
        self.project_dir = Path(project_dir).resolve()
        self.node = None
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 8)
        self.title = QLabel('Select a TileMap2D')
        self.title.setStyleSheet('font-weight:700')
        lay.addWidget(self.title)
        form = QFormLayout()
        self.texture = QLineEdit()
        tr = QHBoxLayout()
        tr.addWidget(self.texture, 1)
        pick = QPushButton('…')
        pick.clicked.connect(self._pick)
        tr.addWidget(pick)
        form.addRow('Atlas', tr)
        self.tw = QSpinBox()
        self.tw.setRange(1, 1024)
        self.tw.setValue(32)
        self.th = QSpinBox()
        self.th.setRange(1, 1024)
        self.th.setValue(32)
        self.cols = QSpinBox()
        self.cols.setRange(1, 1024)
        self.cols.setValue(8)
        self.tile = QSpinBox()
        self.tile.setRange(-1, 999999)
        self.x = QSpinBox()
        self.x.setRange(-10000, 10000)
        self.y = QSpinBox()
        self.y.setRange(-10000, 10000)
        form.addRow('Tile Width', self.tw)
        form.addRow('Tile Height', self.th)
        form.addRow('Atlas Columns', self.cols)
        form.addRow('Selected Tile', self.tile)
        self.paint_view = QCheckBox('Paint with left click in 2D Viewport')
        self.paint_view.toggled.connect(self._paint_settings)
        self.tile.valueChanged.connect(self._paint_settings)
        form.addRow('Viewport Paint', self.paint_view)
        form.addRow('Cell X', self.x)
        form.addRow('Cell Y', self.y)
        lay.addLayout(form)
        row = QHBoxLayout()
        paint = QPushButton('Paint Cell')
        paint.clicked.connect(self.paint)
        erase = QPushButton('Erase')
        erase.clicked.connect(self.erase)
        row.addWidget(paint)
        row.addWidget(erase)
        lay.addLayout(row)
        row2 = QHBoxLayout()
        fill = QPushButton('Fill 10×6')
        fill.clicked.connect(self.fill_demo)
        clear = QPushButton('Clear Map')
        clear.clicked.connect(self.clear)
        row2.addWidget(fill)
        row2.addWidget(clear)
        lay.addLayout(row2)
        lay.addStretch(1)
        self.texture.editingFinished.connect(self._settings)
        self.tw.valueChanged.connect(self._settings)
        self.th.valueChanged.connect(self._settings)
        self.cols.valueChanged.connect(self._settings)

    def set_node(self, node):
        self.node = node if isinstance(node, TileMap2D) else None
        if self.node:
            n = self.node
            self.title.setText(f'TileMap: {n.name} — {len(n.tiles)} cells')
            self.texture.setText(n.texture_path)
            self.tw.setValue(int(n.tile_size.x))
            self.th.setValue(int(n.tile_size.y))
            self.cols.setValue(n.atlas_columns)
        else:
            self.title.setText('Select a TileMap2D')

    def _pick(self):
        p, _ = QFileDialog.getOpenFileName(self, 'Tile Atlas', str(self.project_dir / 'assets'), 'Images (*.png *.jpg *.jpeg *.bmp *.webp)')
        if p:
            try:
                p = Path(p).resolve().relative_to(self.project_dir).as_posix()
            except ValueError:
                pass
            self.texture.setText(str(p))
            self._settings()

    def _settings(self, *_):
        if self.node:
            self.node.texture_path = self.texture.text().strip().replace('\\', '/')
            self.node.tile_size = Vector2(self.tw.value(), self.th.value())
            self.node.atlas_columns = self.cols.value()
            self.changed.emit(self.node)

    def _paint_settings(self, *_):
        self.paint_settings_changed.emit(self.paint_view.isChecked(), self.tile.value())

    def paint(self):
        if self.node:
            self.node.set_tile(self.x.value(), self.y.value(), self.tile.value())
            self.set_node(self.node)
            self.changed.emit(self.node)

    def erase(self):
        if self.node:
            self.node.erase_tile(self.x.value(), self.y.value())
            self.set_node(self.node)
            self.changed.emit(self.node)

    def fill_demo(self):
        if self.node:
            for y in range(6):
                for x in range(10):
                    self.node.set_tile(x, y, self.tile.value())
            self.set_node(self.node)
            self.changed.emit(self.node)

    def clear(self):
        if self.node:
            self.node.tiles.clear()
            self.set_node(self.node)
            self.changed.emit(self.node)
