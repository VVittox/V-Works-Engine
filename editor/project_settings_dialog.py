from __future__ import annotations
from pathlib import Path
import shutil
from PySide6.QtWidgets import QCheckBox, QComboBox, QColorDialog, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QSpinBox, QDoubleSpinBox, QTabWidget, QVBoxLayout, QWidget
from engine.core.project_config import ProjectConfig

class ProjectSettingsDialog(QDialog):

    def __init__(self, config: ProjectConfig, parent=None) -> None:
        super().__init__(parent)
        self.config = config
        self.setWindowTitle('Project Settings')
        self.resize(720, 560)
        outer = QVBoxLayout(self)
        tabs = QTabWidget()
        outer.addWidget(tabs, 1)
        general = QWidget()
        form = QFormLayout(general)
        self.name = QLineEdit(config.name)
        self.main_scene = QLineEdit(config.main_scene)
        scene_row = QHBoxLayout()
        scene_row.addWidget(self.main_scene, 1)
        scene_btn = QPushButton('Browse…')
        scene_btn.clicked.connect(self._pick_scene)
        scene_row.addWidget(scene_btn)
        self.icon = QLineEdit(config.icon)
        icon_row = QHBoxLayout()
        icon_row.addWidget(self.icon, 1)
        icon_btn = QPushButton('Browse…')
        icon_btn.clicked.connect(self._pick_icon)
        icon_row.addWidget(icon_btn)
        form.addRow('Project name', self.name)
        form.addRow('Startup scene', scene_row)
        form.addRow('Game icon', icon_row)
        tabs.addTab(general, 'General')
        display = QWidget()
        df = QFormLayout(display)
        self.width = QSpinBox()
        self.width.setRange(320, 16384)
        self.width.setValue(config.window.width)
        self.height = QSpinBox()
        self.height.setRange(240, 16384)
        self.height.setValue(config.window.height)
        self.fullscreen = QCheckBox()
        self.fullscreen.setChecked(config.window.fullscreen)
        self.borderless = QCheckBox()
        self.borderless.setChecked(config.window.borderless)
        self.resizable = QCheckBox()
        self.resizable.setChecked(config.window.resizable)
        self.vsync = QCheckBox()
        self.vsync.setChecked(config.window.vsync)
        df.addRow('Width', self.width)
        df.addRow('Height', self.height)
        df.addRow('Fullscreen', self.fullscreen)
        df.addRow('Borderless', self.borderless)
        df.addRow('Resizable', self.resizable)
        df.addRow('VSync', self.vsync)
        tabs.addTab(display, 'Display')
        runtime = QWidget()
        rf = QFormLayout(runtime)
        self.preview_backend = QComboBox()
        self.preview_backend.addItem('Legacy Qt preview', 'legacy')
        self.preview_backend.addItem('Engine runtime Game View (2D + 3D)', 'engine')
        idx = self.preview_backend.findData(config.runtime.preview_backend)
        self.preview_backend.setCurrentIndex(max(0, idx))
        self.render_backend = QComboBox()
        self.render_backend.addItem('CPU — compatible software renderer', 'cpu')
        self.render_backend.addItem('GPU — OpenGL 3.3 (experimental)', 'gpu')
        self.render_backend.addItem('Auto — GPU or CPU fallback', 'auto')
        idx = self.render_backend.findData(config.runtime.render_backend)
        self.render_backend.setCurrentIndex(max(0, idx))
        self.render_backend.setToolTip('GPU needs: pip install moderngl glcontext. The current GPU path reads frames back for Pygame/Qt.')
        self.target_fps = QSpinBox()
        self.target_fps.setRange(0, 1000)
        self.target_fps.setSpecialValueText('Unlimited')
        self.target_fps.setValue(config.runtime.target_fps)
        self.physics_fps = QSpinBox()
        self.physics_fps.setRange(10, 1000)
        self.physics_fps.setValue(config.runtime.physics_fps)
        self.gravity = QDoubleSpinBox()
        self.gravity.setRange(-100000, 100000)
        self.gravity.setValue(config.runtime.gravity)
        self.gravity_3d = QDoubleSpinBox()
        self.gravity_3d.setRange(-10000, 10000)
        self.gravity_3d.setDecimals(3)
        self.gravity_3d.setValue(config.runtime.gravity_3d)
        self.debug_overlay = QCheckBox('Show FPS + node count in game')
        self.debug_overlay.setChecked(config.runtime.debug_overlay)
        self.debug_collisions = QCheckBox('Draw collision shapes in runtime')
        self.debug_collisions.setChecked(config.runtime.debug_collisions)
        self.profiler_overlay = QCheckBox('Show profiler timing in runtime overlay')
        self.profiler_overlay.setChecked(config.runtime.profiler_overlay)
        self.bg_button = QPushButton(f'RGB {config.runtime.background_color}')
        self.bg_button.clicked.connect(self._pick_bg)
        self._bg = tuple(config.runtime.background_color)
        rf.addRow('Game View', self.preview_backend)
        rf.addRow('3D renderer', self.render_backend)
        rf.addRow('Target FPS', self.target_fps)
        rf.addRow('Physics FPS', self.physics_fps)
        rf.addRow('Gravity 2D Y', self.gravity)
        rf.addRow('Gravity 3D Y', self.gravity_3d)
        rf.addRow('Default background', self.bg_button)
        rf.addRow('Debug overlay', self.debug_overlay)
        rf.addRow('Debug collisions', self.debug_collisions)
        rf.addRow('Profiler overlay', self.profiler_overlay)
        tabs.addTab(runtime, 'Runtime')
        editor = QWidget()
        ef = QFormLayout(editor)
        self.autosave_enabled = QCheckBox()
        self.autosave_enabled.setChecked(config.editor.autosave_enabled)
        self.autosave_seconds = QSpinBox()
        self.autosave_seconds.setRange(10, 3600)
        self.autosave_seconds.setValue(config.editor.autosave_seconds)
        self.recovery_keep = QSpinBox()
        self.recovery_keep.setRange(1, 100)
        self.recovery_keep.setValue(config.editor.recovery_keep)
        self.grid_size = QSpinBox()
        self.grid_size.setRange(1, 512)
        self.grid_size.setValue(config.editor.grid_size)
        self.show_collision_shapes = QCheckBox()
        self.show_collision_shapes.setChecked(config.editor.show_collision_shapes)
        ef.addRow('Autosave', self.autosave_enabled)
        ef.addRow('Autosave interval (s)', self.autosave_seconds)
        ef.addRow('Recovery snapshots', self.recovery_keep)
        ef.addRow('Grid size', self.grid_size)
        ef.addRow('Editor collision overlay', self.show_collision_shapes)
        tabs.addTab(editor, 'Editor')
        build = QWidget()
        bf = QFormLayout(build)
        self.product_name = QLineEdit(config.build.product_name)
        self.version = QLineEdit(config.build.version)
        self.company = QLineEdit(config.build.company)
        self.onefile = QCheckBox('Single EXE (slower startup)')
        self.onefile.setChecked(config.build.onefile)
        self.debug_console = QCheckBox('Console window (debug build)')
        self.debug_console.setChecked(config.build.debug_console)
        self.clean_build = QCheckBox('Clean PyInstaller cache before build')
        self.clean_build.setChecked(config.build.clean_build)
        bf.addRow('Product name', self.product_name)
        bf.addRow('Version', self.version)
        bf.addRow('Company', self.company)
        bf.addRow('Windows package', self.onefile)
        bf.addRow('Debug', self.debug_console)
        bf.addRow('Build cache', self.clean_build)
        info = QLabel('Scene order is configured in Build → Build Scenes. When the editor itself is packaged, Windows export uses its bundled runtime and does not require PyInstaller on the target machine.')
        info.setWordWrap(True)
        bf.addRow(info)
        tabs.addTab(build, 'Build')
        buttons = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Save)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)

    def _pick_scene(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, 'Choose Startup Scene', str(self.config.root / 'scenes'), 'V Works Scene (*.vscene)')
        if path:
            try:
                self.main_scene.setText(Path(path).resolve().relative_to(self.config.root).as_posix())
            except ValueError:
                self.main_scene.setText(path)

    def _pick_icon(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, 'Choose Game Icon', str(self.config.root), 'Images (*.png *.ico *.jpg *.jpeg)')
        if path:
            try:
                self.icon.setText(Path(path).resolve().relative_to(self.config.root).as_posix())
            except ValueError:
                self.icon.setText(path)

    def _pick_bg(self) -> None:
        from PySide6.QtGui import QColor
        color = QColorDialog.getColor(QColor(*self._bg), self, 'Default Background')
        if color.isValid():
            self._bg = (color.red(), color.green(), color.blue())
            self.bg_button.setText(f'RGB {self._bg}')

    def apply(self) -> None:
        c = self.config
        c.name = self.name.text().strip() or c.name
        scene_text = self.main_scene.text().strip() or c.main_scene
        path = Path(scene_text)
        if path.is_absolute():
            try:
                scene_text = path.resolve().relative_to(c.root).as_posix()
            except ValueError:
                pass
        c.set_main_scene(scene_text)
        icon_text = self.icon.text().strip() or c.icon
        icon_path = Path(icon_text).expanduser()
        if icon_path.is_absolute() and icon_path.exists():
            suffix = icon_path.suffix.lower() if icon_path.suffix else '.png'
            dest = c.root / f'icon{suffix}'
            if icon_path.resolve() != dest.resolve():
                shutil.copy2(icon_path, dest)
            c.icon = dest.name
        else:
            c.icon = icon_text
        c.window.width = self.width.value()
        c.window.height = self.height.value()
        c.window.fullscreen = self.fullscreen.isChecked()
        c.window.borderless = self.borderless.isChecked()
        c.window.resizable = self.resizable.isChecked()
        c.window.vsync = self.vsync.isChecked()
        c.runtime.preview_backend = str(self.preview_backend.currentData())
        c.runtime.render_backend = str(self.render_backend.currentData())
        c.runtime.target_fps = self.target_fps.value()
        c.runtime.physics_fps = self.physics_fps.value()
        c.runtime.gravity = self.gravity.value()
        c.runtime.gravity_3d = self.gravity_3d.value()
        c.runtime.debug_overlay = self.debug_overlay.isChecked()
        c.runtime.debug_collisions = self.debug_collisions.isChecked()
        c.runtime.profiler_overlay = self.profiler_overlay.isChecked()
        c.runtime.background_color = self._bg
        c.editor.autosave_enabled = self.autosave_enabled.isChecked()
        c.editor.autosave_seconds = self.autosave_seconds.value()
        c.editor.recovery_keep = self.recovery_keep.value()
        c.editor.grid_size = self.grid_size.value()
        c.editor.show_collision_shapes = self.show_collision_shapes.isChecked()
        c.build.product_name = self.product_name.text().strip() or c.name
        c.build.version = self.version.text().strip() or '0.1.0'
        c.build.company = self.company.text().strip() or 'VVittox'
        c.build.onefile = self.onefile.isChecked()
        c.build.debug_console = self.debug_console.isChecked()
        c.build.clean_build = self.clean_build.isChecked()
        c.save()
