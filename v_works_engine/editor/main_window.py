from __future__ import annotations
import importlib.util
import json
import os
import sys
from pathlib import Path
from PySide6.QtCore import QProcess, QTimer, QUrl, Qt
from PySide6.QtGui import QAction, QActionGroup, QDesktopServices, QIcon, QKeySequence, QTextCursor
from PySide6.QtWidgets import QFileDialog, QFileSystemModel, QDockWidget, QHBoxLayout, QLabel, QMainWindow, QMessageBox, QPlainTextEdit, QTabBar, QTabWidget, QToolBar, QTreeView, QVBoxLayout, QWidget
from engine.core.project_config import ProjectConfig
from engine.scene import AudioStreamPlayer2D, Button2D, Camera2DNode, CollisionRect2D, ColorRect2D, Label2D, Node, Node2D, Node3D, Scene, Sprite2D, Timer, TileMap2D, ParticleSystem2D, CanvasLayer, Control, UIPanel, UILabel, Light2D, CanvasModulate, Navigation2D, NavigationAgent2D, MeshInstance3D, Camera3DNode, DirectionalLight3D, PointLight3D, SpotLight3D, WorldEnvironment3D, Marker3D, RayCast3D
from engine.physics import CharacterBody2D, RigidBody2D, StaticBody2D, Area2D, CharacterBody3D, RigidBody3D, StaticBody3D, Area3D
from engine.scene.serialization import create_inherited_scene, load_prefab, load_scene, node_from_dict, node_to_dict, save_prefab, save_scene as write_scene
from engine.utils.vmath import Vector2, Vector3
from .build_system import assert_windows_build_host, prepare_windows_build
from .build_scenes_dialog import BuildScenesDialog
from .create_node_dialog import CreateNodeDialog
from .input_map_dialog import InputMapDialog
from .project_settings_dialog import ProjectSettingsDialog
from .asset_importer_dialog import AssetImporterDialog
from .plugin_manager import PluginHost, PluginManagerDialog
from .recovery_dialog import RecoveryDialog
from .resource_editor import ResourceEditorDialog
from .signals_dialog import SignalsDialog
from .tags_layers_dialog import TagsLayersDialog
from .scene_document import SceneDocument
from .widgets.asset_browser import AssetBrowserWidget
from .widgets.diagnostics import SceneDiagnosticsWidget
from .widgets.inspector import InspectorWidget
from .widgets.scene_tree import SceneTreeWidget
from .widgets.viewport import Viewport2D
from .widgets.viewport3d import Viewport3D
from .widgets.game_view import GameView
from .widgets.profiler_widget import ProfilerWidget
from .widgets.python_console import PythonConsoleWidget
from .widgets.tilemap_panel import TileMapPanel
from .widgets.navigation_panel import NavigationPanel
STYLE = '\nQMainWindow, QWidget { background: #202126; color: #d9dce3; }\nQMenuBar, QMenu, QToolBar { background: #292b31; color: #e5e7eb; }\nQDockWidget::title { background: #2b2d33; padding: 6px; text-align: left; }\nQTreeWidget, QTreeView, QPlainTextEdit, QLineEdit, QSpinBox, QDoubleSpinBox, QListWidget, QTabBar {\n    background: #25272c; color: #dce0e8; border: 1px solid #343740; selection-background-color: #315b86;\n}\nQTabBar::tab { background:#282a30; padding:7px 16px; border-right:1px solid #383b43; }\nQTabBar::tab:selected { background:#343842; color:#78baff; }\nQGroupBox { border: 1px solid #3a3d46; margin-top: 10px; padding-top: 8px; font-weight: 600; }\nQGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px; }\nQToolButton:checked { background:#315b86; }\nQToolButton:hover { background: #3a3d45; }\n'

class MainWindow(QMainWindow):

    def __init__(self, project_dir: str | Path | None=None, resources_dir: str | Path | None=None) -> None:
        super().__init__()
        self.engine_root = Path(__file__).resolve().parents[1]
        self.resources_dir = Path(resources_dir or Path(__file__).resolve().parent / 'resources').resolve()
        self.project_dir = Path(project_dir or os.getcwd()).resolve()
        self.project = ProjectConfig.load_or_create(self.project_dir, self.resources_dir)
        self.documents: list[SceneDocument] = []
        self._history: dict[int, dict[str, object]] = {}
        self._node_clipboard: dict | None = None
        self._build_process: QProcess | None = None
        self._play_process: QProcess | None = None
        self._last_build_output: Path | None = None
        self._script_path: Path | None = None
        self.resize(1540, 920)
        self.setStyleSheet(STYLE)
        self.setDockNestingEnabled(True)
        self._apply_icon()
        central = QWidget()
        c_layout = QVBoxLayout(central)
        c_layout.setContentsMargins(0, 0, 0, 0)
        c_layout.setSpacing(0)
        self.scene_tabs = QTabBar()
        self.scene_tabs.setTabsClosable(True)
        self.scene_tabs.setMovable(True)
        self.scene_tabs.currentChanged.connect(self._tab_changed)
        self.scene_tabs.tabCloseRequested.connect(self._close_scene_tab)
        self.scene_tabs.tabMoved.connect(self._tab_moved)
        c_layout.addWidget(self.scene_tabs)
        self.workspace_tabs = QTabWidget(self)
        self.workspace_tabs.setDocumentMode(True)
        self.viewport = Viewport2D(self)
        self.viewport3d = Viewport3D(self)
        self.viewport3d.set_project_dir(self.project_dir)
        self.viewport.set_project_dir(self.project_dir)
        self.viewport.set_game_size(self.project.window.width, self.project.window.height)
        self.viewport.snap_size = float(self.project.editor.grid_size)
        self.viewport.show_collision = self.project.editor.show_collision_shapes
        self.game_view = GameView(self.project, self)
        self.workspace_tabs.addTab(self.viewport, '2D Scene')
        self.workspace_tabs.addTab(self.viewport3d, '3D Scene')
        self.workspace_tabs.addTab(self.game_view, 'Game')
        c_layout.addWidget(self.workspace_tabs, 1)
        self.setCentralWidget(central)
        self.scene_tree = SceneTreeWidget(self)
        self.inspector = InspectorWidget(self)
        self.inspector.set_project_config(self.project)
        self.output = QPlainTextEdit(self)
        self.output.setReadOnly(True)
        self.output.setMaximumBlockCount(5000)
        self.diagnostics = SceneDiagnosticsWidget(self)
        self.profiler_widget = ProfilerWidget(self)
        self.tilemap_panel = TileMapPanel(self.project_dir, self)
        self.navigation_panel = NavigationPanel(self)
        self.python_console = PythonConsoleWidget(self, self)
        self.script_editor = QPlainTextEdit(self)
        self.script_editor.setTabStopDistance(32)
        self.script_editor.setPlaceholderText('Double-click a .py file or attach/open a script from Inspector.')
        self.script_status = QLabel('No script open')
        script_panel = QWidget()
        sp = QVBoxLayout(script_panel)
        sp.setContentsMargins(2, 2, 2, 2)
        sp.addWidget(self.script_status)
        sp.addWidget(self.script_editor, 1)
        self.asset_browser = AssetBrowserWidget(self.project_dir, self)
        self.asset_browser.asset_activated.connect(self._open_asset_path)
        self.fs_model = QFileSystemModel(self)
        self.fs_model.setRootPath(str(self.project_dir))
        self.fs_view = QTreeView(self)
        self.fs_view.setModel(self.fs_model)
        self.fs_view.setRootIndex(self.fs_model.index(str(self.project_dir)))
        self.fs_view.setDragEnabled(True)
        for col in (1, 2, 3):
            self.fs_view.hideColumn(col)
        self.fs_view.doubleClicked.connect(self._filesystem_open)
        self._dock('Scene', self.scene_tree, Qt.LeftDockWidgetArea)
        self._dock('Inspector', self.inspector, Qt.RightDockWidgetArea)
        self.fs_dock = self._dock('FileSystem', self.fs_view, Qt.BottomDockWidgetArea)
        self.assets_dock = self._dock('Asset Browser', self.asset_browser, Qt.BottomDockWidgetArea)
        self.tabifyDockWidget(self.fs_dock, self.assets_dock)
        self.assets_dock.raise_()
        self.output_dock = self._dock('Output', self.output, Qt.BottomDockWidgetArea)
        self.output_dock.hide()
        self.script_dock = self._dock('Script Editor', script_panel, Qt.BottomDockWidgetArea)
        self.script_dock.hide()
        self.diagnostics_dock = self._dock('Diagnostics', self.diagnostics, Qt.RightDockWidgetArea)
        self.diagnostics_dock.hide()
        self.profiler_dock = self._dock('Profiler', self.profiler_widget, Qt.RightDockWidgetArea)
        self.profiler_dock.hide()
        self.tilemap_dock = self._dock('TileMap', self.tilemap_panel, Qt.RightDockWidgetArea)
        self.tilemap_dock.hide()
        self.navigation_dock = self._dock('Navigation', self.navigation_panel, Qt.RightDockWidgetArea)
        self.navigation_dock.hide()
        self.console_dock = self._dock('Console', self.python_console, Qt.BottomDockWidgetArea)
        self.console_dock.hide()
        self.scene_tree.node_selected.connect(self.select_node)
        self.scene_tree.hierarchy_changed.connect(self._node_changed)
        self.viewport.node_selected.connect(self.select_node)
        self.viewport.node_changed.connect(self._node_changed)
        self.viewport3d.node_selected.connect(self.select_node)
        self.viewport3d.node_changed.connect(self._node_changed)
        self.viewport.asset_dropped.connect(self._asset_dropped)
        self.inspector.property_changed.connect(self._node_changed)
        self.inspector.script_open_requested.connect(self.open_script)
        self.tilemap_panel.changed.connect(self._node_changed)
        self.tilemap_panel.paint_settings_changed.connect(self.viewport.set_tile_paint)
        self.navigation_panel.changed.connect(self._node_changed)
        self.game_view.profiler_updated.connect(self.profiler_widget.update_stats)
        self.game_view.state_changed.connect(lambda state: self.statusBar().showMessage(f'Game View: {state}', 2500))
        self._build_actions()
        self._build_menu()
        self._build_toolbar()
        self._open_initial_scene()
        self.statusBar().showMessage(str(self.project_dir))
        self.log(f'V Works Engine ready — {self.project.name}')
        self.plugin_host = PluginHost(self.project_dir, self.project.enabled_plugins)
        self.plugin_host.load_enabled(self)
        self.autosave_timer = QTimer(self)
        self.autosave_timer.setInterval(max(10, self.project.editor.autosave_seconds) * 1000)
        self.autosave_timer.timeout.connect(self._autosave)
        if self.project.editor.autosave_enabled:
            self.autosave_timer.start()
        QTimer.singleShot(350, self._offer_recovery)

    @property
    def document(self) -> SceneDocument:
        return self.documents[max(0, self.scene_tabs.currentIndex())]

    @property
    def selected(self) -> Node:
        return getattr(self, '_selected', self.document.scene)

    @selected.setter
    def selected(self, node: Node) -> None:
        self._selected = node

    def _snapshot(self, doc: SceneDocument | None=None) -> str:
        return json.dumps(node_to_dict((doc or self.document).scene), sort_keys=True)

    def _ensure_history(self, doc: SceneDocument) -> dict[str, object]:
        return self._history.setdefault(id(doc), {'undo': [], 'redo': [], 'last': self._snapshot(doc)})

    def _commit_history(self) -> None:
        h = self._ensure_history(self.document)
        now = self._snapshot()
        if now == h['last']:
            return
        undo = h['undo']
        undo.append(h['last'])
        del undo[:-100]
        h['redo'].clear()
        h['last'] = now

    def undo(self) -> None:
        h = self._ensure_history(self.document)
        undo = h['undo']
        if not undo:
            return
        current = self._snapshot()
        state = undo.pop()
        h['redo'].append(current)
        h['last'] = state
        self._restore_snapshot(state)
        self.log('Undo')

    def redo(self) -> None:
        h = self._ensure_history(self.document)
        redo = h['redo']
        if not redo:
            return
        current = self._snapshot()
        state = redo.pop()
        h['undo'].append(current)
        h['last'] = state
        self._restore_snapshot(state)
        self.log('Redo')

    def _restore_snapshot(self, state: str) -> None:
        root = node_from_dict(json.loads(state))
        if not isinstance(root, Scene):
            scene = Scene(root.name)
            [scene.add_child(c) for c in root.get_children()]
            root = scene
        self.document.scene = root
        self.document.mark_dirty()
        self.selected = root
        self._sync_document()
        self._update_title()

    def _open_initial_scene(self) -> None:
        path = self.project.main_scene_path
        try:
            doc = SceneDocument.load(path) if path.exists() else SceneDocument(Scene('Main'), path)
        except Exception as exc:
            self.log(f'Could not load main scene: {exc}')
            doc = SceneDocument(Scene('Main'), path)
        self._add_document(doc)

    def _add_document(self, doc: SceneDocument, switch=True) -> int:
        if doc.path:
            for i, d in enumerate(self.documents):
                if d.path and d.path.resolve() == doc.path.resolve():
                    if switch:
                        self.scene_tabs.setCurrentIndex(i)
                    return i
        self.documents.append(doc)
        idx = self.scene_tabs.addTab(doc.display_name)
        self._ensure_history(doc)
        if switch:
            self.scene_tabs.setCurrentIndex(idx)
        return idx

    def _tab_moved(self, from_index: int, to_index: int) -> None:
        if from_index == to_index or from_index < 0 or to_index < 0:
            return
        doc = self.documents.pop(from_index)
        self.documents.insert(to_index, doc)
        self._tab_changed(self.scene_tabs.currentIndex())

    def _tab_changed(self, index: int) -> None:
        if index < 0 or index >= len(self.documents):
            return
        self.selected = self.documents[index].scene
        self._sync_document()

    def _close_scene_tab(self, index: int) -> None:
        if index < 0 or index >= len(self.documents):
            return
        doc = self.documents[index]
        if not self._confirm_doc(doc):
            return
        self.documents.pop(index)
        self._history.pop(id(doc), None)
        self.scene_tabs.removeTab(index)
        if not self.documents:
            self._add_document(SceneDocument(Scene('Main')))
        self._tab_changed(self.scene_tabs.currentIndex())

    def _apply_icon(self) -> None:
        candidates = [self.project.icon_path, self.resources_dir / 'vworks_icon.png', self.resources_dir / 'vworks_icon.ico']
        icon = next((p for p in candidates if p.exists()), None)
        if icon:
            self.setWindowIcon(QIcon(str(icon)))

    def _dock(self, title, widget, area):
        dock = QDockWidget(title, self)
        dock.setObjectName(f"dock_{title.lower().replace(' ', '_')}")
        dock.setWidget(widget)
        self.addDockWidget(area, dock)
        return dock

    def _action(self, text, slot, shortcut=None, checkable=False):
        act = QAction(text, self)
        act.triggered.connect(slot)
        act.setCheckable(checkable)
        if shortcut:
            act.setShortcut(shortcut)
        return act

    def _build_actions(self):
        self.act_new = self._action('New Scene', self.new_scene, QKeySequence.New)
        self.act_open = self._action('Open Scene…', self.open_scene, QKeySequence.Open)
        self.act_save = self._action('Save', self.save_scene, QKeySequence.Save)
        self.act_save_as = self._action('Save As…', self.save_scene_as, QKeySequence.SaveAs)
        self.act_save_all = self._action('Save All', self.save_all, 'Ctrl+Shift+S')
        self.act_undo = self._action('Undo', self.undo, QKeySequence.Undo)
        self.act_redo = self._action('Redo', self.redo, QKeySequence.Redo)
        self.act_copy = self._action('Copy Node', self.copy_node, QKeySequence.Copy)
        self.act_paste = self._action('Paste Node', self.paste_node, QKeySequence.Paste)
        self.act_duplicate = self._action('Duplicate Node', self.duplicate_selected, 'Ctrl+D')
        self.act_project_settings = self._action('Project Settings…', self.show_project_settings)
        self.act_input_map = self._action('Input Map…', self.show_input_map)
        self.act_tags_layers = self._action('Tags, Layers & Groups…', self.show_tags_layers)
        self.act_plugins = self._action('Package / Plugin Manager…', self.show_plugins)
        self.act_import_assets = self._action('Import Assets…', self.show_asset_importer, 'Ctrl+I')
        self.act_recovery = self._action('Autosave / Recovery…', self.show_recovery)
        self.act_new_material = self._action('New Material…', lambda: self.new_resource('Material2D'))
        self.act_new_shader = self._action('New Shader…', lambda: self.new_resource('Shader2D'))
        self.act_new_tileset = self._action('New TileSet…', lambda: self.new_resource('TileSet2D'))
        self.act_create_node = self._action('+ Add Node…', self.show_create_node, 'Ctrl+A')
        self.act_delete = self._action('Delete Node', self.delete_selected, QKeySequence.Delete)
        self.act_signals = self._action('Signals…', self.show_signals, 'Ctrl+Shift+C')
        self.act_inherited = self._action('Create Inherited Scene…', self.create_inherited_scene)
        self.act_attach_script = self._action('Attach New Script…', self.attach_new_script, 'Ctrl+Alt+A')
        self.act_save_script = self._action('Save Script', self.save_script, 'Ctrl+Alt+S')
        self.act_detach_script = self._action('Detach Script', self.detach_script)
        self.act_save_prefab = self._action('Save Selected as Prefab…', self.save_selected_prefab, 'Ctrl+Shift+P')
        self.act_instance_prefab = self._action('Instantiate Prefab…', self.instantiate_prefab, 'Ctrl+Alt+P')
        self.act_play_project = self._action('▶ Play Project (External)', self.play_project, 'F5')
        self.act_play_scene = self._action('▷ Play Scene (External)', self.play_scene, 'F6')
        self.act_stop = self._action('■ Stop External', self.stop_game, 'F8')
        self.act_game_play = self._action('▶ Play In Editor', self.play_in_editor, 'Ctrl+F5')
        self.act_game_pause = self._action('⏸ Pause', self.pause_in_editor, 'F7')
        self.act_game_step = self._action('⏭ Step Frame', self.step_in_editor, 'F10')
        self.act_game_stop = self._action('■ Stop In Editor', self.stop_in_editor, 'Shift+F8')
        self.act_center = self._action('Frame Selected', self.frame_selected, 'F')
        self.act_camera_preview = self._action('Camera Preview [P]', self.viewport3d.toggle_pilot_camera)
        self.act_snap = self._action('Snap Grid', self._toggle_snap, checkable=True)
        self.act_move = self._action('Move [W]', lambda: self._set_gizmo('move'), 'W', True)
        self.act_rotate = self._action('Rotate [E]', lambda: self._set_gizmo('rotate'), 'E', True)
        self.act_scale = self._action('Scale [R]', lambda: self._set_gizmo('scale'), 'R', True)
        self.act_move.setChecked(True)
        self.act_build_scenes = self._action('Build Scenes…', self.show_build_scenes)
        self.act_build_windows = self._action('Build Windows…', self.build_windows)
        self.act_build_run = self._action('Build & Run Windows', self.build_and_run_windows)
        self.act_cancel_build = self._action('Cancel Build', self.cancel_build)
        self.act_open_builds = self._action('Open Builds Folder', self.open_builds_folder)
        self.act_output = self._action('Output', lambda: self.output_dock.setVisible(not self.output_dock.isVisible()), 'Ctrl+J')
        self.act_script = self._action('Script Editor', lambda: self.script_dock.setVisible(not self.script_dock.isVisible()), 'Ctrl+Alt+J')
        self.act_diagnostics = self._action('Diagnostics', lambda: self.diagnostics_dock.setVisible(not self.diagnostics_dock.isVisible()), 'Ctrl+Shift+J')
        self.act_view_2d = self._action('2D View', lambda: self.workspace_tabs.setCurrentWidget(self.viewport), 'Ctrl+1')
        self.act_view_3d = self._action('3D View', lambda: self.workspace_tabs.setCurrentWidget(self.viewport3d), 'Ctrl+2')
        self.act_game_tab = self._action('Game View', lambda: self.workspace_tabs.setCurrentWidget(self.game_view), 'Ctrl+3')
        self.act_tilemap = self._action('TileMap Panel', lambda: self.tilemap_dock.setVisible(not self.tilemap_dock.isVisible()))
        self.act_navigation = self._action('Navigation Panel', lambda: self.navigation_dock.setVisible(not self.navigation_dock.isVisible()))
        self.act_profiler = self._action('Profiler', lambda: self.profiler_dock.setVisible(not self.profiler_dock.isVisible()))
        self.act_console = self._action('Python Console', lambda: self.console_dock.setVisible(not self.console_dock.isVisible()), 'Ctrl+`')
        self.act_debug_collision = self._action('Debug Collision Overlay', self._toggle_debug_collision, checkable=True)
        self.act_debug_collision.setChecked(self.project.editor.show_collision_shapes)
        self.act_reset_layout = self._action('Reset Editor Layout', self.reset_layout)

    def _build_menu(self):
        f = self.menuBar().addMenu('File')
        [f.addAction(a) for a in (self.act_new, self.act_open, self.act_save, self.act_save_as, self.act_save_all, self.act_import_assets, self.act_recovery)]
        e = self.menuBar().addMenu('Edit')
        [e.addAction(a) for a in (self.act_undo, self.act_redo, self.act_copy, self.act_paste, self.act_duplicate, self.act_delete)]
        p = self.menuBar().addMenu('Project')
        [p.addAction(a) for a in (self.act_project_settings, self.act_input_map, self.act_tags_layers, self.act_plugins)]
        resources = self.menuBar().addMenu('Resources')
        [resources.addAction(a) for a in (self.act_new_material, self.act_new_shader, self.act_new_tileset)]
        sm = self.menuBar().addMenu('Scene')
        [sm.addAction(a) for a in (self.act_create_node, self.act_signals, self.act_inherited, self.act_attach_script, self.act_detach_script, self.act_save_prefab, self.act_instance_prefab)]
        r = self.menuBar().addMenu('Run')
        [r.addAction(a) for a in (self.act_game_play, self.act_game_pause, self.act_game_step, self.act_game_stop, self.act_play_project, self.act_play_scene, self.act_stop)]
        b = self.menuBar().addMenu('Build')
        [b.addAction(a) for a in (self.act_build_scenes, self.act_build_windows, self.act_build_run, self.act_cancel_build, self.act_open_builds)]
        v = self.menuBar().addMenu('View')
        [v.addAction(a) for a in (self.act_snap, self.act_move, self.act_rotate, self.act_scale, self.act_camera_preview, self.act_view_2d, self.act_view_3d, self.act_game_tab, self.act_tilemap, self.act_navigation, self.act_profiler, self.act_console, self.act_debug_collision, self.act_output, self.act_script, self.act_diagnostics, self.act_reset_layout)]

    def _build_toolbar(self):
        bar = QToolBar('Main', self)
        bar.setMovable(False)
        self.addToolBar(bar)
        bar.addAction(self.act_create_node)
        bar.addSeparator()
        bar.addAction(self.act_undo)
        bar.addAction(self.act_redo)
        bar.addSeparator()
        group = QActionGroup(self)
        group.setExclusive(True)
        [group.addAction(a) for a in (self.act_move, self.act_rotate, self.act_scale)]
        [bar.addAction(a) for a in (self.act_move, self.act_rotate, self.act_scale)]
        bar.addAction(self.act_snap)
        bar.addAction(self.act_center)
        bar.addAction(self.act_camera_preview)
        bar.addSeparator()
        bar.addAction(self.act_game_play)
        bar.addAction(self.act_game_pause)
        bar.addAction(self.act_game_step)
        bar.addAction(self.act_game_stop)
        bar.addSeparator()
        bar.addAction(self.act_play_project)
        bar.addAction(self.act_stop)
        bar.addSeparator()
        bar.addAction(self.act_build_scenes)
        mode = QLabel('  V WORKS ENGINE 2D / 3D  ')
        mode.setStyleSheet('font-weight:700;color:#68aefc')
        bar.addWidget(mode)

    def log(self, text: str) -> None:
        self.output.appendPlainText(text)

    def select_node(self, node: Node) -> None:
        self.selected = node
        self.scene_tree.select_node(node)
        self.viewport.select_node(node)
        self.viewport3d.select_node(node)
        self.inspector.set_node(node)
        self.tilemap_panel.set_node(node)
        self.navigation_panel.set_node(node)
        self.statusBar().showMessage(node.path)

    def _node_changed(self, node: Node) -> None:
        self.document.mark_dirty()
        self._commit_history()
        self.scene_tree.refresh(node)
        self.viewport.update()
        self.viewport3d.update()
        self.inspector.set_node(node)
        self._refresh_diagnostics()
        self._update_title()

    def _parent_for_new_node(self) -> Node:
        return self.selected if self.selected is not None else self.document.scene

    def show_create_node(self) -> None:
        d = CreateNodeDialog(self)
        if d.exec() and d.selected_type():
            self.add_node(d.selected_type())

    def _new_node(self, kind: str) -> Node:
        factories = {'Node': lambda: Node('Node'), 'Node2D': lambda: Node2D('Node2D'), 'Node3D': lambda: Node3D('Node3D'), 'MeshInstance3D': lambda: MeshInstance3D('MeshInstance3D'), 'Camera3D': lambda: Camera3DNode('Camera3D'), 'DirectionalLight3D': lambda: DirectionalLight3D('DirectionalLight3D'), 'PointLight3D': lambda: PointLight3D('PointLight3D'), 'SpotLight3D': lambda: SpotLight3D('SpotLight3D'), 'WorldEnvironment3D': lambda: WorldEnvironment3D('WorldEnvironment3D'), 'Marker3D': lambda: Marker3D('Marker3D'), 'RayCast3D': lambda: RayCast3D('RayCast3D'), 'StaticBody3D': lambda: StaticBody3D('StaticBody3D'), 'RigidBody3D': lambda: RigidBody3D('RigidBody3D'), 'CharacterBody3D': lambda: CharacterBody3D('CharacterBody3D'), 'Area3D': lambda: Area3D('Area3D'), 'ColorRect2D': lambda: ColorRect2D('ColorRect2D'), 'Sprite2D': lambda: Sprite2D('Sprite2D'), 'Label2D': lambda: Label2D('Label2D'), 'Camera2D': lambda: Camera2DNode('Camera2D'), 'StaticBody2D': lambda: StaticBody2D('StaticBody2D'), 'RigidBody2D': lambda: RigidBody2D('RigidBody2D'), 'CharacterBody2D': lambda: CharacterBody2D('CharacterBody2D'), 'Area2D': lambda: Area2D('Area2D'), 'CollisionRect2D': lambda: CollisionRect2D('CollisionRect2D'), 'Timer': lambda: Timer('Timer'), 'AudioStreamPlayer2D': lambda: AudioStreamPlayer2D('AudioStreamPlayer2D'), 'Button2D': lambda: Button2D('Button2D'), 'TileMap2D': lambda: TileMap2D('TileMap2D'), 'ParticleSystem2D': lambda: ParticleSystem2D('ParticleSystem2D'), 'CanvasLayer': lambda: CanvasLayer('CanvasLayer'), 'Control': lambda: Control('Control'), 'UIPanel': lambda: UIPanel('UIPanel'), 'UILabel': lambda: UILabel('UILabel'), 'Light2D': lambda: Light2D('Light2D'), 'CanvasModulate': lambda: CanvasModulate('CanvasModulate'), 'Navigation2D': lambda: Navigation2D('Navigation2D'), 'NavigationAgent2D': lambda: NavigationAgent2D('NavigationAgent2D')}
        return factories.get(kind, lambda: Node(kind))()

    def add_node(self, kind: str) -> None:
        parent = self._parent_for_new_node()
        node = self._new_node(kind)
        if isinstance(node, Node2D) and isinstance(parent, Node2D):
            node.position = Vector2(32, 32)
        parent.add_child(node)
        self.document.mark_dirty()
        self._commit_history()
        self.scene_tree.refresh(node)
        self.select_node(node)
        self.viewport.update()
        self._update_title()
        self.log(f'Added {kind}: {node.path}')

    def delete_selected(self) -> None:
        node = self.selected
        if node is self.document.scene:
            self.log('Scene root cannot be deleted')
            return
        parent = node.parent
        if parent:
            parent.remove_child(node)
        self.document.mark_dirty()
        self._commit_history()
        self.selected = parent or self.document.scene
        self.scene_tree.refresh(self.selected)
        self.select_node(self.selected)
        self.viewport.update()
        self._update_title()

    def copy_node(self) -> None:
        if self.selected is self.document.scene:
            return
        self._node_clipboard = node_to_dict(self.selected)
        self.log(f'Copied node: {self.selected.name}')

    def paste_node(self) -> None:
        if not self._node_clipboard:
            return
        node = node_from_dict(json.loads(json.dumps(self._node_clipboard)))
        node.name = f'{node.name}_Copy'
        self._parent_for_new_node().add_child(node)
        self.document.mark_dirty()
        self._commit_history()
        self.scene_tree.refresh(node)
        self.select_node(node)
        self.viewport.update()

    def duplicate_selected(self) -> None:
        self.copy_node()
        self.paste_node()

    def _asset_dropped(self, path: str, world) -> None:
        p = Path(path).resolve()
        try:
            rel = p.relative_to(self.project_dir).as_posix()
        except ValueError:
            QMessageBox.warning(self, 'Asset outside project', 'Copy the image into the project assets folder before dropping it into the scene.')
            return
        node = Sprite2D(p.stem, rel)
        node.position = Vector2(float(world.x()), float(world.y()))
        self.document.scene.add_child(node)
        self.document.mark_dirty()
        self._commit_history()
        self.scene_tree.refresh(node)
        self.select_node(node)
        self.viewport.update()
        self.log(f'Created Sprite2D from {rel}')

    def _set_gizmo(self, mode: str) -> None:
        self.viewport.set_gizmo_mode(mode)
        self.viewport3d.set_gizmo_mode(mode)
        self.act_move.setChecked(mode == 'move')
        self.act_rotate.setChecked(mode == 'rotate')
        self.act_scale.setChecked(mode == 'scale')

    def _toggle_snap(self, checked: bool) -> None:
        self.viewport.snap_enabled = checked
        self.viewport3d.snap_enabled = checked
        self.viewport.update()
        self.viewport3d.update()

    def frame_selected(self) -> None:
        if self.workspace_tabs.currentWidget() is self.viewport3d:
            self.viewport3d.frame_selected()
        else:
            self.viewport.frame_selected()

    def new_scene(self) -> None:
        self._add_document(SceneDocument(Scene('Main')))

    def open_scene(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, 'Open V Works Scene', str(self.project_dir / 'scenes'), 'V Works Scene (*.vscene)')
        if path:
            try:
                self._add_document(SceneDocument.load(path))
                self.log(f'Opened {path}')
            except Exception as exc:
                QMessageBox.critical(self, 'Open failed', str(exc))

    def save_scene(self) -> bool:
        if self.document.path is None:
            return self.save_scene_as()
        try:
            self.document.save()
            self._ensure_history(self.document)['last'] = self._snapshot()
            self._update_title()
            self.log(f'Saved {self.document.path}')
            return True
        except Exception as exc:
            QMessageBox.critical(self, 'Save failed', str(exc))
            return False

    def save_scene_as(self) -> bool:
        d = self.project_dir / 'scenes'
        d.mkdir(exist_ok=True)
        path, _ = QFileDialog.getSaveFileName(self, 'Save V Works Scene', str(d / 'scene.vscene'), 'V Works Scene (*.vscene)')
        if not path:
            return False
        if not path.lower().endswith('.vscene'):
            path += '.vscene'
        try:
            self.document.save(path)
            self.scene_tabs.setTabText(self.scene_tabs.currentIndex(), self.document.display_name)
            self._ensure_history(self.document)['last'] = self._snapshot()
            self._update_title()
            self.log(f'Saved {path}')
            return True
        except Exception as exc:
            QMessageBox.critical(self, 'Save failed', str(exc))
            return False

    def save_all(self) -> bool:
        original = self.scene_tabs.currentIndex()
        for i, doc in enumerate(self.documents):
            if not doc.dirty:
                continue
            self.scene_tabs.setCurrentIndex(i)
            if not self.save_scene():
                self.scene_tabs.setCurrentIndex(original)
                return False
        self.scene_tabs.setCurrentIndex(original)
        return True

    def save_selected_prefab(self) -> None:
        if self.selected is self.document.scene:
            QMessageBox.information(self, 'Prefab', 'Select a non-root node first.')
            return
        folder = self.project_dir / 'assets' / 'prefabs'
        folder.mkdir(parents=True, exist_ok=True)
        path, _ = QFileDialog.getSaveFileName(self, 'Save Prefab', str(folder / f'{self.selected.name}.vprefab'), 'V Works Prefab (*.vprefab)')
        if not path:
            return
        if not path.lower().endswith('.vprefab'):
            path += '.vprefab'
        try:
            save_prefab(self.selected, path)
            self.log(f'Saved prefab: {path}')
        except Exception as exc:
            QMessageBox.critical(self, 'Prefab', str(exc))

    def instantiate_prefab(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, 'Instantiate Prefab', str(self.project_dir / 'assets' / 'prefabs'), 'V Works Prefab (*.vprefab)')
        if not path:
            return
        try:
            node = load_prefab(path)
            self._parent_for_new_node().add_child(node)
            self.document.mark_dirty()
            self._commit_history()
            self.scene_tree.refresh(node)
            self.select_node(node)
            self.viewport.update()
            self.log(f'Instantiated prefab: {Path(path).name}')
        except Exception as exc:
            QMessageBox.critical(self, 'Prefab', str(exc))

    def attach_new_script(self) -> None:
        node = self.selected
        scripts = self.project_dir / 'scripts'
        scripts.mkdir(exist_ok=True)
        default = scripts / f"{node.name.lower().replace(' ', '_')}.py"
        path, _ = QFileDialog.getSaveFileName(self, 'Create V Works Script', str(default), 'Python (*.py)')
        if not path:
            return
        p = Path(path)
        p = p if p.suffix.lower() == '.py' else p.with_suffix('.py')
        if not p.exists():
            p.write_text('from engine.scripting import VScript\n\n\nclass Script(VScript):\n    def _ready(self):\n        pass\n\n    def _process(self, delta):\n        # Example: self.owner.position.x += 100 * delta\n        pass\n', encoding='utf-8')
        try:
            node.script_path = p.resolve().relative_to(self.project_dir).as_posix()
        except ValueError:
            node.script_path = str(p.resolve())
        self._node_changed(node)
        self.open_script(node.script_path)

    def detach_script(self) -> None:
        if getattr(self.selected, 'script_path', ''):
            self.selected.script_path = ''
            self._node_changed(self.selected)

    def open_script(self, path: str) -> None:
        p = Path(path)
        p = p if p.is_absolute() else self.project_dir / p
        if not p.exists():
            QMessageBox.warning(self, 'Script', f'Script not found:\n{p}')
            return
        try:
            self._script_path = p.resolve()
            self.script_editor.setPlainText(p.read_text(encoding='utf-8'))
            self.script_status.setText(str(self._script_path))
            self.script_dock.show()
            self.script_editor.setFocus()
            self.log(f'Opened script: {p.name}')
        except Exception as exc:
            QMessageBox.critical(self, 'Script', str(exc))

    def save_script(self) -> None:
        if self._script_path is None:
            return
        try:
            self._script_path.write_text(self.script_editor.toPlainText(), encoding='utf-8')
            self.log(f'Saved script: {self._script_path.name}')
        except Exception as exc:
            QMessageBox.critical(self, 'Script', str(exc))

    def show_signals(self) -> None:
        node = self.selected
        before = json.dumps(getattr(node, 'signal_connections', []), sort_keys=True)
        SignalsDialog(self.document.scene, node, self).exec()
        after = json.dumps(getattr(node, 'signal_connections', []), sort_keys=True)
        if before != after:
            self._node_changed(node)
            self.log(f'Signal connections updated: {node.path}')

    def create_inherited_scene(self) -> None:
        base, _ = QFileDialog.getOpenFileName(self, 'Choose Base Scene', str(self.project_dir / 'scenes'), 'V Works Scene (*.vscene)')
        if not base:
            return
        dest, _ = QFileDialog.getSaveFileName(self, 'Create Inherited Scene', str(self.project_dir / 'scenes' / f'{Path(base).stem}_derived.vscene'), 'V Works Scene (*.vscene)')
        if not dest:
            return
        if not dest.lower().endswith('.vscene'):
            dest += '.vscene'
        try:
            create_inherited_scene(base, dest)
            self._add_document(SceneDocument.load(dest))
            self.log(f'Created inherited scene: {Path(dest).name} ← {Path(base).name}')
        except Exception as exc:
            QMessageBox.critical(self, 'Scene Inheritance', str(exc))

    def show_tags_layers(self) -> None:
        d = TagsLayersDialog(self.project, self.document.scene, self)
        if d.exec():
            self.project = ProjectConfig.load(self.project_dir)
            self.inspector.set_project_config(self.project)
            self.inspector.set_node(self.selected)
            self.log('Tags / Layers saved')

    def show_plugins(self) -> None:
        d = PluginManagerDialog(self.project, self)
        if d.exec():
            try:
                self.plugin_host.shutdown(self)
            except Exception:
                pass
            self.project = ProjectConfig.load(self.project_dir)
            self.plugin_host = PluginHost(self.project_dir, self.project.enabled_plugins)
            self.plugin_host.load_enabled(self)
            self.log('Plugin configuration reloaded')

    def show_asset_importer(self) -> None:
        d = AssetImporterDialog(self.project_dir, self)
        if d.exec():
            self.asset_browser.refresh()
            self.log('Asset import finished')

    def new_resource(self, resource_type: str) -> None:
        d = ResourceEditorDialog(self.project_dir, None, resource_type, self)
        if d.exec():
            self.asset_browser.refresh()
            self.log(f'Saved {resource_type}: {d.path}')

    def edit_resource(self, path: str | Path) -> None:
        try:
            d = ResourceEditorDialog(self.project_dir, path, parent=self)
            if d.exec():
                self.asset_browser.refresh()
                self.viewport.update()
                self.log(f'Resource saved: {path}')
        except Exception as exc:
            QMessageBox.critical(self, 'Resource Editor', str(exc))

    def show_recovery(self) -> None:
        d = RecoveryDialog(self.project_dir, self)
        if d.exec() and d.selected_path():
            try:
                scene = load_scene(d.selected_path())
                doc = SceneDocument(scene)
                doc.mark_dirty()
                self._add_document(doc)
                self.log(f'Opened recovery snapshot: {d.selected_path().name}')
            except Exception as exc:
                QMessageBox.critical(self, 'Recovery', str(exc))

    def _offer_recovery(self) -> None:
        folder = self.project_dir / '.vworks' / 'autosave'
        snapshots = list(folder.glob('*.vscene')) if folder.exists() else []
        if not snapshots:
            return
        newest = max((p.stat().st_mtime for p in snapshots))
        saved = max((d.path.stat().st_mtime for d in self.documents if d.path and d.path.exists()), default=0)
        if newest > saved:
            answer = QMessageBox.question(self, 'Recovery snapshots found', 'Newer autosave snapshots exist for this project. Open Recovery?', QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
            if answer == QMessageBox.Yes:
                self.show_recovery()

    def play_in_editor(self) -> None:
        if not self.save_all():
            return
        self.game_view.set_scene_source(self.document.scene)
        self.game_view.debug_collisions = self.act_debug_collision.isChecked()
        self.game_view.play()
        self.workspace_tabs.setCurrentWidget(self.game_view)
        self.profiler_dock.show()
        self.log('Play In Editor started')

    def pause_in_editor(self) -> None:
        self.game_view.toggle_pause()

    def step_in_editor(self) -> None:
        self.game_view.step()
        self.workspace_tabs.setCurrentWidget(self.game_view)

    def stop_in_editor(self) -> None:
        self.game_view.stop()

    def _toggle_debug_collision(self, checked: bool) -> None:
        self.viewport.show_collision = bool(checked)
        self.game_view.debug_collisions = bool(checked)
        self.viewport.update()
        self.game_view.update()

    def show_project_settings(self) -> None:
        d = ProjectSettingsDialog(self.project, self)
        if d.exec():
            try:
                d.apply()
                self.project = ProjectConfig.load(self.project_dir)
                self.inspector.set_project_config(self.project)
                self.game_view.set_project(self.project)
                self.viewport.set_game_size(self.project.window.width, self.project.window.height)
                self.viewport.snap_size = float(self.project.editor.grid_size)
                self.act_debug_collision.setChecked(self.project.editor.show_collision_shapes)
                self._toggle_debug_collision(self.project.editor.show_collision_shapes)
                self.autosave_timer.setInterval(max(10, self.project.editor.autosave_seconds) * 1000)
                self.autosave_timer.start() if self.project.editor.autosave_enabled else self.autosave_timer.stop()
                self._apply_icon()
                self._update_title()
                self.log('Project settings saved')
            except Exception as exc:
                QMessageBox.critical(self, 'Project Settings', str(exc))

    def show_input_map(self) -> None:
        d = InputMapDialog(self.project, self)
        if d.exec():
            self.project = ProjectConfig.load(self.project_dir)
            self.log('Input Map saved')

    def show_build_scenes(self) -> None:
        d = BuildScenesDialog(self.project, self.document.path, self)
        if d.exec():
            self.project = ProjectConfig.load(self.project_dir)
            self.log(f'Build Scenes saved: {len(self.project.enabled_build_scenes)} enabled')

    def _save_before_run(self) -> bool:
        return self.save_all()

    def _start_play(self, args: list[str], label: str) -> None:
        self.stop_game()
        self.output_dock.show()
        p = QProcess(self)
        self._play_process = p
        p.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        p.readyReadStandardOutput.connect(self._read_play_output)
        p.finished.connect(lambda code, status: self.log(f'\n=== GAME STOPPED ({code}) ==='))
        p.setProgram(args[0])
        p.setArguments(args[1:])
        p.setWorkingDirectory(str(self.engine_root))
        p.start()
        self.log(f'=== {label} ===')

    def play_project(self) -> None:
        if self._save_before_run():
            args = [sys.executable, '--run-project', str(self.project_dir)] if getattr(sys, 'frozen', False) else [sys.executable, '-m', 'engine.runtime_game', str(self.project_dir)]
            self._start_play(args, f'PLAY PROJECT: {self.project.name}')

    def play_scene(self) -> None:
        if not self._save_before_run() or self.document.path is None:
            return
        if getattr(sys, 'frozen', False):
            args = [sys.executable, '--run-scene', str(self.document.path), str(self.project_dir)]
        else:
            runner = Path(__file__).with_name('runner.py')
            args = [sys.executable, str(runner), str(self.document.path), str(self.project_dir)]
        self._start_play(args, f'PLAY SCENE: {self.document.display_name}')

    def stop_game(self) -> None:
        if self._play_process is not None and self._play_process.state() != QProcess.ProcessState.NotRunning:
            self._play_process.kill()
            self._play_process.waitForFinished(1500)
            self.log('Game stopped by editor')

    def _read_play_output(self) -> None:
        if self._play_process:
            text = bytes(self._play_process.readAllStandardOutput()).decode('utf-8', errors='replace')
            self.output.moveCursor(QTextCursor.MoveOperation.End)
            self.output.insertPlainText(text)

    def build_windows(self, run_after=False) -> None:
        if self._build_process is not None and self._build_process.state() != QProcess.ProcessState.NotRunning:
            QMessageBox.information(self, 'Build', 'A build is already running.')
            return
        if not self._save_before_run():
            return
        try:
            assert_windows_build_host()
            if not getattr(sys, 'frozen', False) and importlib.util.find_spec('PyInstaller') is None:
                raise RuntimeError('PyInstaller is not installed. Run: .\\.venv\\Scripts\\python.exe -m pip install -r requirements.txt')
            self.project = ProjectConfig.load(self.project_dir)
            plan = prepare_windows_build(self.project, self.engine_root, default_icon=self.resources_dir / 'vworks_icon.ico')
        except Exception as exc:
            QMessageBox.critical(self, 'Windows build', str(exc))
            return
        self.output_dock.show()
        self.output.clear()
        self.log(f"=== BUILD WINDOWS: {plan.executable_name} ===\nBackend: {plan.backend}\nScenes: {', '.join((s.path for s in self.project.enabled_build_scenes))}\n")
        if plan.backend == 'frozen-runtime-copy' and self.project.build.onefile:
            self.log('OneFile is not available from the packaged editor without an external Python/PyInstaller toolchain; exporting a portable folder build instead.\n')
        self._last_build_output = plan.output_dir
        process = QProcess(self)
        self._build_process = process
        process.setProperty('run_after', bool(run_after))
        process.setProperty('exe_name', plan.executable_name)
        process.setProperty('backend', plan.backend)
        process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        process.readyReadStandardOutput.connect(self._read_build_output)
        process.finished.connect(self._build_finished)
        process.errorOccurred.connect(lambda err: self.log(f'Build process error: {err}'))
        process.setProgram(plan.command[0])
        process.setArguments(plan.command[1:])
        process.setWorkingDirectory(str(self.engine_root))
        process.start()

    def build_and_run_windows(self) -> None:
        self.build_windows(True)

    def cancel_build(self) -> None:
        if self._build_process is not None and self._build_process.state() != QProcess.ProcessState.NotRunning:
            self._build_process.kill()
            self.log('\n=== BUILD CANCELLED ===')

    def _read_build_output(self) -> None:
        if self._build_process:
            text = bytes(self._build_process.readAllStandardOutput()).decode('utf-8', errors='replace')
            self.output.moveCursor(QTextCursor.MoveOperation.End)
            self.output.insertPlainText(text)

    def _build_finished(self, exit_code: int, exit_status) -> None:
        p = self._build_process
        if exit_code == 0:
            self.log('\n=== BUILD SUCCESS ===')
            self.statusBar().showMessage(f'Build completed: {self._last_build_output}', 10000)
            if p and p.property('run_after'):
                name = str(p.property('exe_name'))
                candidates = [self._last_build_output / name / f'{name}.exe', self._last_build_output / f'{name}.exe']
                exe = next((x for x in candidates if x.exists()), None)
                if exe:
                    QProcess.startDetached(str(exe), [], str(exe.parent))
            else:
                QMessageBox.information(self, 'Build complete', f'Windows build completed.\n\nOutput:\n{self._last_build_output}')
        else:
            self.log(f'\n=== BUILD FAILED (exit code {exit_code}) ===')
            backend = str(p.property('backend')) if p else 'build'
            QMessageBox.critical(self, 'Build failed', f'Build backend {backend} failed. Open Output for details.')

    def open_builds_folder(self) -> None:
        p = self.project_dir / 'builds' / 'windows'
        p.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(p)))

    def _autosave(self) -> None:
        if not self.project.editor.autosave_enabled:
            return
        import datetime, hashlib
        folder = self.project_dir / '.vworks' / 'autosave'
        folder.mkdir(parents=True, exist_ok=True)
        count = 0
        manifest = {'format': 'vworks_recovery', 'version': 1, 'entries': []}
        for i, doc in enumerate(self.documents):
            if not doc.dirty:
                continue
            original = ''
            if doc.path:
                try:
                    original = doc.path.resolve().relative_to(self.project_dir).as_posix()
                except ValueError:
                    original = str(doc.path)
            stem = (doc.path.stem if doc.path else f'untitled_{i}').replace(' ', '_')
            key = hashlib.sha1((original or stem).encode('utf-8')).hexdigest()[:8]
            stamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            snapshot = folder / f'{stem}_{key}_{stamp}.autosave.vscene'
            try:
                write_scene(doc.scene, snapshot)
                count += 1
                manifest['entries'].append({'original': original, 'snapshot': snapshot.name, 'time': stamp})
                candidates = sorted(folder.glob(f'{stem}_{key}_*.autosave.vscene'), key=lambda x: x.stat().st_mtime, reverse=True)
                for old in candidates[max(1, self.project.editor.recovery_keep):]:
                    try:
                        old.unlink()
                    except OSError:
                        pass
            except Exception as exc:
                self.log(f'Autosave failed for {doc.display_name}: {exc}')
        if count:
            (folder / 'recovery.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
            self.statusBar().showMessage(f'Autosaved {count} dirty scene(s)', 2500)

    def _open_asset_path(self, path_text: str) -> None:
        path = Path(path_text)
        suffix = path.suffix.lower()
        if suffix == '.vscene':
            try:
                self._add_document(SceneDocument.load(path))
                self.log(f'Opened {path}')
            except Exception as exc:
                QMessageBox.critical(self, 'Open failed', str(exc))
        elif suffix == '.py':
            self.open_script(str(path))
        elif suffix == '.vprefab':
            try:
                n = load_prefab(path)
                self._parent_for_new_node().add_child(n)
                self.document.mark_dirty()
                self._commit_history()
                self.scene_tree.refresh(n)
                self.select_node(n)
                self.viewport.update()
            except Exception as exc:
                QMessageBox.critical(self, 'Prefab', str(exc))
        elif suffix in {'.vmat', '.vshader', '.vtileset', '.vres'}:
            self.edit_resource(path)
        elif suffix in {'.png', '.jpg', '.jpeg', '.bmp', '.webp'}:
            try:
                rel = path.resolve().relative_to(self.project_dir).as_posix()
            except ValueError:
                return
            n = Sprite2D(path.stem, rel)
            self.document.scene.add_child(n)
            self.document.mark_dirty()
            self._commit_history()
            self.scene_tree.refresh(n)
            self.select_node(n)
        elif suffix in {'.obj', '.stl'}:
            try:
                rel = path.resolve().relative_to(self.project_dir).as_posix()
            except ValueError:
                return
            n = MeshInstance3D(path.stem, 'cube')
            n.mesh_path = rel
            self.document.scene.add_child(n)
            self.document.mark_dirty()
            self._commit_history()
            self.scene_tree.refresh(n)
            self.select_node(n)
            self.workspace_tabs.setCurrentWidget(self.viewport3d)
            self.viewport.update()

    def _filesystem_open(self, index) -> None:
        self._open_asset_path(self.fs_model.filePath(index))

    def _sync_document(self) -> None:
        self.scene_tree.set_scene(self.document.scene)
        self.viewport.set_scene(self.document.scene)
        self.viewport3d.set_scene(self.document.scene)
        self.game_view.set_scene_source(self.document.scene)
        self.select_node(self.document.scene)
        self._refresh_diagnostics()
        self._update_title()

    def _refresh_diagnostics(self) -> None:
        try:
            self.diagnostics.refresh(self.document.scene, self.project_dir, len(self.project.enabled_build_scenes))
        except Exception:
            pass

    def _update_title(self) -> None:
        for i, d in enumerate(self.documents):
            self.scene_tabs.setTabText(i, d.display_name + (' *' if d.dirty else ''))
        self.setWindowTitle(f"V Works Engine — {self.project.name} — {self.document.display_name}{('*' if self.document.dirty else '')}")

    def _confirm_doc(self, doc: SceneDocument) -> bool:
        if not doc.dirty:
            return True
        answer = QMessageBox.question(self, 'Unsaved scene', f'Save changes to {doc.display_name}?', QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel, QMessageBox.Save)
        if answer == QMessageBox.Cancel:
            return False
        if answer == QMessageBox.Save:
            idx = self.documents.index(doc)
            old = self.scene_tabs.currentIndex()
            self.scene_tabs.setCurrentIndex(idx)
            ok = self.save_scene()
            self.scene_tabs.setCurrentIndex(old)
            return ok
        return True

    def reset_layout(self) -> None:
        for dock in self.findChildren(QDockWidget):
            dock.show()
        self.output_dock.hide()
        self.script_dock.hide()
        self.statusBar().showMessage('Editor layout reset', 3000)

    def closeEvent(self, event) -> None:
        for doc in list(self.documents):
            if not self._confirm_doc(doc):
                event.ignore()
                return
        self.stop_game()
        self.stop_in_editor()
        self.cancel_build()
        try:
            self.plugin_host.shutdown(self)
        except Exception:
            pass
        event.accept()
