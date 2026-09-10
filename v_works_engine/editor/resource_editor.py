from __future__ import annotations
import json
from pathlib import Path
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFileDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit, QPushButton, QSpinBox, QTabWidget, QVBoxLayout, QWidget, QColorDialog
from engine.resources import Material2D, Shader2D, TileSetResource, VResource

class ResourceEditorDialog(QDialog):

    def __init__(self, project_dir, path: str | Path | None=None, resource_type: str='Material2D', parent=None):
        super().__init__(parent)
        self.project_dir = Path(project_dir).resolve()
        self.path = Path(path).resolve() if path else None
        self.resource = VResource.load(self.path) if self.path and self.path.exists() else {'Material2D': Material2D.default, 'Shader2D': Shader2D.default, 'TileSet2D': TileSetResource.default}.get(resource_type, Material2D.default)()
        self.setWindowTitle(f'Resource Editor — {self.resource.resource_type}')
        self.resize(760, 620)
        outer = QVBoxLayout(self)
        self.form = QFormLayout()
        outer.addLayout(self.form)
        self.widgets = {}
        self._build()
        buttons = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Save)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)

    def _build(self):
        d = self.resource.data
        typ = self.resource.resource_type
        pathlabel = QLabel(str(self.path) if self.path else 'New resource')
        pathlabel.setWordWrap(True)
        self.form.addRow('File', pathlabel)
        if typ == 'Material2D':
            preset = QComboBox()
            preset.addItems(['none', 'grayscale', 'invert', 'pixelate', 'tint'])
            preset.setCurrentText(str(d.get('shader_preset', 'none')))
            self.widgets['shader_preset'] = preset
            self.form.addRow('CPU Shader Preset', preset)
            blend = QComboBox()
            blend.addItems(['alpha', 'add', 'multiply'])
            blend.setCurrentText(str(d.get('blend_mode', 'alpha')))
            self.widgets['blend_mode'] = blend
            self.form.addRow('Blend Mode', blend)
            self.tint = list(d.get('tint', [255, 255, 255, 255]))
            b = QPushButton(f'RGBA {tuple(self.tint)}')
            b.clicked.connect(lambda: self._pick_tint(b))
            self.form.addRow('Tint', b)
            shader = QLineEdit(str(d.get('shader', '')))
            row = QHBoxLayout()
            row.addWidget(shader, 1)
            pick = QPushButton('…')
            pick.clicked.connect(lambda: self._pick_file(shader, 'Shaders (*.vshader)'))
            row.addWidget(pick)
            self.widgets['shader'] = shader
            self.form.addRow('Shader Resource', row)
            px = QSpinBox()
            px.setRange(1, 64)
            px.setValue(int(dict(d.get('params', {})).get('pixel_size', 4)))
            self.widgets['pixel_size'] = px
            self.form.addRow('Pixel Size', px)
        elif typ == 'Shader2D':
            preset = QComboBox()
            preset.addItems(['none', 'grayscale', 'invert', 'pixelate', 'tint'])
            preset.setCurrentText(str(d.get('preset', 'none')))
            self.widgets['preset'] = preset
            self.form.addRow('Preset', preset)
            code = QPlainTextEdit(str(d.get('code', '')))
            code.setMinimumHeight(360)
            self.widgets['code'] = code
            self.form.addRow('VSL Metadata / Notes', code)
            self.form.addRow(QLabel('V Works Engine uses CPU shader presets in Pygame. .vshader files are reusable and build-safe.'))
        elif typ == 'TileSet2D':
            tex = QLineEdit(str(d.get('texture', '')))
            row = QHBoxLayout()
            row.addWidget(tex, 1)
            pick = QPushButton('…')
            pick.clicked.connect(lambda: self._pick_file(tex, 'Images (*.png *.jpg *.jpeg *.bmp *.webp)'))
            row.addWidget(pick)
            self.widgets['texture'] = tex
            self.form.addRow('Atlas Texture', row)
            for key, label, lo, hi in (('tile_width', 'Tile Width', 1, 4096), ('tile_height', 'Tile Height', 1, 4096), ('columns', 'Columns', 1, 4096), ('margin', 'Margin', 0, 1024), ('spacing', 'Spacing', 0, 1024)):
                w = QSpinBox()
                w.setRange(lo, hi)
                w.setValue(int(d.get(key, 32 if 'tile_' in key else 8 if key == 'columns' else 0)))
                self.widgets[key] = w
                self.form.addRow(label, w)

    def _pick_tint(self, b):
        c = QColorDialog.getColor(QColor(*self.tint[:4]), self, 'Tint')
        if c.isValid():
            self.tint = [c.red(), c.green(), c.blue(), c.alpha()]
            b.setText(f'RGBA {tuple(self.tint)}')

    def _pick_file(self, edit, filter_text):
        p, _ = QFileDialog.getOpenFileName(self, 'Select Resource', str(self.project_dir / 'assets'), filter_text)
        if p:
            try:
                p = Path(p).resolve().relative_to(self.project_dir).as_posix()
            except ValueError:
                pass
            edit.setText(str(p))

    def _save(self):
        d = dict(self.resource.data)
        typ = self.resource.resource_type
        if typ == 'Material2D':
            d.update(shader_preset=self.widgets['shader_preset'].currentText(), blend_mode=self.widgets['blend_mode'].currentText(), tint=self.tint, shader=self.widgets['shader'].text().strip().replace('\\', '/'), params={'pixel_size': self.widgets['pixel_size'].value()})
        elif typ == 'Shader2D':
            d.update(preset=self.widgets['preset'].currentText(), code=self.widgets['code'].toPlainText())
        elif typ == 'TileSet2D':
            for k, w in self.widgets.items():
                d[k] = w.text().strip().replace('\\', '/') if isinstance(w, QLineEdit) else w.value()
        self.resource.data = d
        if self.path is None:
            ext = {'Material2D': 'vmat', 'Shader2D': 'vshader', 'TileSet2D': 'vtileset'}.get(typ, 'vres')
            folder = self.project_dir / 'assets' / {'Material2D': 'materials', 'Shader2D': 'shaders', 'TileSet2D': 'tilesets'}.get(typ, 'resources')
            folder.mkdir(parents=True, exist_ok=True)
            p, _ = QFileDialog.getSaveFileName(self, 'Save Resource', str(folder / f'new.{ext}'), f'V Works Resource (*.{ext})')
            if not p:
                return
            self.path = Path(p).with_suffix(f'.{ext}') if Path(p).suffix.lower() != f'.{ext}' else Path(p)
        self.resource.save(self.path)
        self.accept()
