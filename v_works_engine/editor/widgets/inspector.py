from __future__ import annotations
import math
from pathlib import Path
from PySide6.QtCore import Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QCheckBox, QColorDialog, QComboBox, QDoubleSpinBox, QFileDialog, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QScrollArea, QSpinBox, QVBoxLayout, QWidget
from engine.scene import AudioStreamPlayer2D, Button2D, Camera2DNode, CollisionRect2D, ColorRect2D, Label2D, Node, Node2D, Node3D, Sprite2D, Timer, TileMap2D, ParticleSystem2D, Control, UIPanel, UILabel, Light2D, CanvasModulate, Navigation2D, NavigationAgent2D, CanvasLayer, MeshInstance3D, Camera3DNode, DirectionalLight3D, PointLight3D, SpotLight3D, WorldEnvironment3D, Marker3D, RayCast3D
from engine.physics import PhysicsBody2D, PhysicsBody3D

class InspectorWidget(QScrollArea):
    property_changed = Signal(object)
    script_open_requested = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWidgetResizable(True)
        self._node: Node | None = None
        self.project_dir = Path.cwd()
        self.project = None
        self._body = QWidget()
        self._layout = QVBoxLayout(self._body)
        self._layout.setContentsMargins(8, 8, 8, 8)
        self._layout.setSpacing(8)
        self.setWidget(self._body)

    def set_project_dir(self, path: str | Path) -> None:
        self.project_dir = Path(path).resolve()

    def set_project_config(self, project) -> None:
        self.project = project
        self.project_dir = Path(project.root).resolve()

    def set_node(self, node: Node | None) -> None:
        self._node = node
        while self._layout.count():
            item = self._layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        if node is None:
            self._layout.addStretch(1)
            return
        base = QGroupBox(node.__class__.__name__)
        form = QFormLayout(base)
        name = QLineEdit(node.name)
        name.editingFinished.connect(lambda: self._set_name(name.text()))
        form.addRow('Name', name)
        ident = QLineEdit(str(node.id))
        ident.setReadOnly(True)
        form.addRow('ID', ident)
        script = QLineEdit(getattr(node, 'script_path', ''))
        row = QHBoxLayout()
        row.addWidget(script, 1)
        browse = QPushButton('…')
        browse.setFixedWidth(30)
        browse.clicked.connect(lambda: self._pick_script(script))
        row.addWidget(browse)
        open_btn = QPushButton('Open')
        open_btn.clicked.connect(lambda: self._open_script(script.text()))
        row.addWidget(open_btn)
        script.editingFinished.connect(lambda: self._set_attr('script_path', script.text().strip().replace('\\', '/')))
        form.addRow('Script', row)
        groups = QLineEdit(', '.join(sorted(getattr(node, 'groups', set()))))
        groups.editingFinished.connect(lambda: self._set_groups(groups.text()))
        form.addRow('Groups', groups)
        tag = QComboBox()
        tag.setEditable(True)
        tag.addItems(getattr(self.project, 'tags', ['Untagged']))
        tag.setCurrentText(getattr(node, 'tag', 'Untagged'))
        tag.currentTextChanged.connect(lambda v: self._set_attr('tag', v.strip() or 'Untagged'))
        form.addRow('Tag', tag)
        layer = QComboBox()
        layers = getattr(self.project, 'layers', [f'Layer {i}' for i in range(32)])
        [layer.addItem(f'{i}: {name}', i) for i, name in enumerate(layers[:32])]
        idx = max(0, min(31, int(getattr(node, 'layer', 0))))
        layer.setCurrentIndex(idx)
        layer.currentIndexChanged.connect(lambda i: self._set_attr('layer', i))
        form.addRow('Layer', layer)
        locked = self._check(bool(getattr(node, 'editor_locked', False)), lambda v: self._set_attr('editor_locked', v))
        form.addRow('Editor Locked', locked)
        self._layout.addWidget(base)
        if isinstance(node, Node2D):
            g = QGroupBox('Transform 2D')
            f = QFormLayout(g)
            px = self._float(node.position.x)
            py = self._float(node.position.y)
            rot = self._float(math.degrees(node.rotation), -360000, 360000)
            sx = self._float(node.scale.x, -1000, 1000)
            sy = self._float(node.scale.y, -1000, 1000)
            vis = QCheckBox()
            vis.setChecked(node.visible)
            z = QSpinBox()
            z.setRange(-4096, 4096)
            z.setValue(node.z_index)
            px.valueChanged.connect(lambda v: self._set_vec('position', 0, v))
            py.valueChanged.connect(lambda v: self._set_vec('position', 1, v))
            rot.valueChanged.connect(lambda v: self._set_attr('rotation', math.radians(v)))
            sx.valueChanged.connect(lambda v: self._set_vec('scale', 0, v))
            sy.valueChanged.connect(lambda v: self._set_vec('scale', 1, v))
            vis.toggled.connect(lambda v: self._set_attr('visible', v))
            z.valueChanged.connect(lambda v: self._set_attr('z_index', v))
            f.addRow('Position X', px)
            f.addRow('Position Y', py)
            f.addRow('Rotation °', rot)
            f.addRow('Scale X', sx)
            f.addRow('Scale Y', sy)
            f.addRow('Visible', vis)
            f.addRow('Z Index', z)
            mat = QLineEdit(getattr(node, 'material_path', ''))
            mr = QHBoxLayout()
            mr.addWidget(mat, 1)
            mb = QPushButton('…')
            mb.setFixedWidth(30)
            mb.clicked.connect(lambda: self._pick_material(mat))
            mr.addWidget(mb)
            mat.editingFinished.connect(lambda: self._set_attr('material_path', mat.text().strip().replace('\\', '/')))
            f.addRow('Material', mr)
            self._layout.addWidget(g)
        if isinstance(node, Node3D):
            g = QGroupBox('Transform 3D')
            f = QFormLayout(g)
            px = self._float(node.position.x)
            py = self._float(node.position.y)
            pz = self._float(node.position.z)
            rx = self._float(math.degrees(node.rotation.x), -360000, 360000)
            ry = self._float(math.degrees(node.rotation.y), -360000, 360000)
            rz = self._float(math.degrees(node.rotation.z), -360000, 360000)
            sx = self._float(node.scale.x, -1000, 1000)
            sy = self._float(node.scale.y, -1000, 1000)
            sz = self._float(node.scale.z, -1000, 1000)
            vis = self._check(node.visible, lambda v: self._set_attr('visible', v))
            layer3 = QSpinBox()
            layer3.setRange(-4096, 4096)
            layer3.setValue(node.render_layer)
            px.valueChanged.connect(lambda v: self._set_vec3('position', 0, v))
            py.valueChanged.connect(lambda v: self._set_vec3('position', 1, v))
            pz.valueChanged.connect(lambda v: self._set_vec3('position', 2, v))
            rx.valueChanged.connect(lambda v: self._set_vec3('rotation', 0, math.radians(v)))
            ry.valueChanged.connect(lambda v: self._set_vec3('rotation', 1, math.radians(v)))
            rz.valueChanged.connect(lambda v: self._set_vec3('rotation', 2, math.radians(v)))
            sx.valueChanged.connect(lambda v: self._set_vec3('scale', 0, v))
            sy.valueChanged.connect(lambda v: self._set_vec3('scale', 1, v))
            sz.valueChanged.connect(lambda v: self._set_vec3('scale', 2, v))
            layer3.valueChanged.connect(lambda v: self._set_attr('render_layer', v))
            f.addRow('Position X', px); f.addRow('Position Y', py); f.addRow('Position Z', pz)
            f.addRow('Rotation X °', rx); f.addRow('Rotation Y °', ry); f.addRow('Rotation Z °', rz)
            f.addRow('Scale X', sx); f.addRow('Scale Y', sy); f.addRow('Scale Z', sz)
            f.addRow('Visible', vis); f.addRow('Render Layer', layer3)
            self._layout.addWidget(g)
        if isinstance(node, PhysicsBody3D):
            g = QGroupBox('PhysicsBody3D')
            f = QFormLayout(g)
            mass = self._float(node.mass, 0.001, 100000)
            gravity = self._float(node.gravity_scale, -1000, 1000)
            rest = self._float(node.restitution, 0, 1)
            friction = self._float(node.friction, 0, 10)
            mass.valueChanged.connect(lambda v: self._set_attr('mass', v))
            gravity.valueChanged.connect(lambda v: self._set_attr('gravity_scale', v))
            rest.valueChanged.connect(lambda v: self._set_attr('restitution', v))
            friction.valueChanged.connect(lambda v: self._set_attr('friction', v))
            cx = self._float(node.collider.size.x, 0.001, 100000)
            cy = self._float(node.collider.size.y, 0.001, 100000)
            cz = self._float(node.collider.size.z, 0.001, 100000)
            cx.valueChanged.connect(lambda v: self._set_collider3d_size(0, v))
            cy.valueChanged.connect(lambda v: self._set_collider3d_size(1, v))
            cz.valueChanged.connect(lambda v: self._set_collider3d_size(2, v))
            enabled = self._check(node.collider.enabled, lambda v: self._set_collider3d('enabled', v))
            trigger = self._check(node.collider.is_trigger, lambda v: self._set_collider3d('is_trigger', v))
            f.addRow('Mass', mass); f.addRow('Gravity Scale', gravity); f.addRow('Restitution', rest); f.addRow('Friction', friction)
            f.addRow('Collider X', cx); f.addRow('Collider Y', cy); f.addRow('Collider Z', cz); f.addRow('Collider Enabled', enabled); f.addRow('Trigger', trigger)
            self._layout.addWidget(g)
        if isinstance(node, MeshInstance3D):
            g = QGroupBox('MeshInstance3D')
            f = QFormLayout(g)
            primitive = QComboBox(); primitive.addItems(['cube', 'sphere', 'plane', 'pyramid', 'cylinder']); primitive.setCurrentText(node.primitive)
            primitive.currentTextChanged.connect(lambda v: self._set_attr('primitive', v))
            mesh_path = QLineEdit(node.mesh_path)
            mesh_row = QHBoxLayout(); mesh_row.addWidget(mesh_path, 1)
            mesh_btn = QPushButton('…'); mesh_btn.setFixedWidth(30); mesh_btn.clicked.connect(lambda: self._pick_mesh3d(mesh_path)); mesh_row.addWidget(mesh_btn)
            mesh_path.editingFinished.connect(lambda: self._set_attr('mesh_path', mesh_path.text().strip().replace('\\', '/')))
            sx3 = self._float(node.size.x, 0.001, 10000); sy3 = self._float(node.size.y, 0.001, 10000); sz3 = self._float(node.size.z, 0.001, 10000)
            sx3.valueChanged.connect(lambda v: self._set_size3d(0, v)); sy3.valueChanged.connect(lambda v: self._set_size3d(1, v)); sz3.valueChanged.connect(lambda v: self._set_size3d(2, v))
            color3 = self._color_button(node.color, lambda c: self._set_color(node, c))
            wire = self._check(node.wireframe, lambda v: self._set_attr('wireframe', v))
            shaded = self._check(node.shaded, lambda v: self._set_attr('shaded', v))
            ds = self._check(node.double_sided, lambda v: self._set_attr('double_sided', v))
            receive_light = self._check(node.receive_light, lambda v: self._set_attr('receive_light', v))
            cast_shadow = self._check(node.cast_shadow, lambda v: self._set_attr('cast_shadow', v))
            seg = QSpinBox(); seg.setRange(6, 64); seg.setValue(node.segments); seg.valueChanged.connect(lambda v: self._set_attr('segments', v))
            rings = QSpinBox(); rings.setRange(4, 48); rings.setValue(node.rings); rings.valueChanged.connect(lambda v: self._set_attr('rings', v))
            f.addRow('Primitive', primitive); f.addRow('Mesh File', mesh_row); f.addRow('Size X', sx3); f.addRow('Size Y', sy3); f.addRow('Size Z', sz3); f.addRow('Color', color3)
            f.addRow('Wireframe', wire); f.addRow('Shaded', shaded); f.addRow('Receive Light', receive_light); f.addRow('Cast Shadow Flag', cast_shadow); f.addRow('Double Sided', ds); f.addRow('Segments', seg); f.addRow('Rings', rings)
            self._layout.addWidget(g)
        if isinstance(node, Camera3DNode):
            g = QGroupBox('Camera3D')
            f = QFormLayout(g)
            current = self._check(node.current, self._set_camera_current)
            fov = self._float(node.fov, 1, 179); near = self._float(node.near, 0.001, 10000); far = self._float(node.far, 0.01, 1000000); ortho_size = self._float(node.ortho_size, 0.01, 100000)
            fov.valueChanged.connect(lambda v: self._set_attr('fov', v)); near.valueChanged.connect(lambda v: self._set_attr('near', v)); far.valueChanged.connect(lambda v: self._set_attr('far', v)); ortho_size.valueChanged.connect(lambda v: self._set_attr('ortho_size', v))
            ortho = self._check(node.orthographic, lambda v: self._set_attr('orthographic', v))
            cull = QLineEdit(f'0x{int(node.cull_mask) & 0xFFFFFFFF:08X}')
            cull.editingFinished.connect(lambda: self._set_int_text_attr('cull_mask', cull.text(), 0xFFFFFFFF))
            f.addRow('Current', current); f.addRow('FOV', fov); f.addRow('Near', near); f.addRow('Far', far); f.addRow('Orthographic', ortho); f.addRow('Ortho Size', ortho_size); f.addRow('Cull Mask', cull)
            self._layout.addWidget(g)
        if isinstance(node, DirectionalLight3D):
            g = QGroupBox('DirectionalLight3D')
            f = QFormLayout(g)
            color3 = self._color_button(node.color, lambda c: self._set_color(node, c))
            energy = self._float(node.energy, 0, 100); ambient = self._float(node.ambient, 0, 10)
            energy.valueChanged.connect(lambda v: self._set_attr('energy', v)); ambient.valueChanged.connect(lambda v: self._set_attr('ambient', v))
            enabled = self._check(node.enabled, lambda v: self._set_attr('enabled', v))
            f.addRow('Color', color3); f.addRow('Energy', energy); f.addRow('Ambient', ambient); f.addRow('Enabled', enabled)
            self._layout.addWidget(g)
        if isinstance(node, PointLight3D):
            g = QGroupBox('SpotLight3D' if isinstance(node, SpotLight3D) else 'PointLight3D')
            f = QFormLayout(g)
            color3 = self._color_button(node.color, lambda c: self._set_color(node, c))
            energy = self._float(node.energy, 0, 1000); energy.valueChanged.connect(lambda v: self._set_attr('energy', v))
            radius = self._float(node.range, 0.001, 100000); radius.valueChanged.connect(lambda v: self._set_attr('range', v))
            attenuation = self._float(node.attenuation, 0.01, 32); attenuation.valueChanged.connect(lambda v: self._set_attr('attenuation', v))
            enabled = self._check(node.enabled, lambda v: self._set_attr('enabled', v))
            f.addRow('Color', color3); f.addRow('Energy', energy); f.addRow('Range', radius); f.addRow('Attenuation', attenuation); f.addRow('Enabled', enabled)
            if isinstance(node, SpotLight3D):
                angle = self._float(node.spot_angle, 1, 179); angle.valueChanged.connect(lambda v: self._set_attr('spot_angle', v))
                softness = self._float(node.edge_softness, 0, 1); softness.setSingleStep(0.05); softness.valueChanged.connect(lambda v: self._set_attr('edge_softness', v))
                f.addRow('Spot Angle °', angle); f.addRow('Edge Softness', softness)
            self._layout.addWidget(g)
        if isinstance(node, RayCast3D):
            g = QGroupBox('RayCast3D')
            f = QFormLayout(g)
            tx = self._float(node.target_position.x); ty = self._float(node.target_position.y); tz = self._float(node.target_position.z)
            tx.valueChanged.connect(lambda v: self._set_vec3('target_position', 0, v)); ty.valueChanged.connect(lambda v: self._set_vec3('target_position', 1, v)); tz.valueChanged.connect(lambda v: self._set_vec3('target_position', 2, v))
            enabled = self._check(node.enabled, lambda v: self._set_attr('enabled', v))
            exclude_parent = self._check(node.exclude_parent, lambda v: self._set_attr('exclude_parent', v))
            mask = QLineEdit(f'0x{int(node.collision_mask) & 0xFFFFFFFF:08X}')
            mask.editingFinished.connect(lambda: self._set_int_text_attr('collision_mask', mask.text(), 0xFFFFFFFF))
            f.addRow('Target X', tx); f.addRow('Target Y', ty); f.addRow('Target Z', tz); f.addRow('Enabled', enabled); f.addRow('Exclude Parent', exclude_parent); f.addRow('Collision Mask', mask); f.addRow('Colliding', QLabel('Yes' if node.colliding else 'No'))
            self._layout.addWidget(g)
        if isinstance(node, WorldEnvironment3D):
            g = QGroupBox('WorldEnvironment3D')
            f = QFormLayout(g)
            ambient_color = self._color_button(node.ambient_color, lambda c: self._set_attr('ambient_color', tuple(c)))
            ambient_energy = self._float(node.ambient_energy, 0, 10); ambient_energy.valueChanged.connect(lambda v: self._set_attr('ambient_energy', v))
            fog = self._check(node.fog_enabled, lambda v: self._set_attr('fog_enabled', v))
            fog_color = self._color_button(node.fog_color, lambda c: self._set_attr('fog_color', tuple(c)))
            fn = self._float(node.fog_near, 0, 100000); ff = self._float(node.fog_far, 0.001, 1000000)
            fn.valueChanged.connect(lambda v: self._set_attr('fog_near', v)); ff.valueChanged.connect(lambda v: self._set_attr('fog_far', v))
            sky = self._check(node.sky_enabled, lambda v: self._set_attr('sky_enabled', v))
            sky_top = self._color_button(node.sky_top_color, lambda c: self._set_attr('sky_top_color', tuple(c)))
            sky_bottom = self._color_button(node.sky_bottom_color, lambda c: self._set_attr('sky_bottom_color', tuple(c)))
            f.addRow('Ambient Color', ambient_color); f.addRow('Ambient Energy', ambient_energy); f.addRow('Fog', fog); f.addRow('Fog Color', fog_color); f.addRow('Fog Near', fn); f.addRow('Fog Far', ff); f.addRow('Sky Gradient', sky); f.addRow('Sky Top', sky_top); f.addRow('Sky Bottom', sky_bottom)
            self._layout.addWidget(g)
        if isinstance(node, ColorRect2D):
            g = QGroupBox('ColorRect2D')
            f = QFormLayout(g)
            sw = self._float(node.size.x, 1, 100000)
            sh = self._float(node.size.y, 1, 100000)
            sw.valueChanged.connect(lambda v: self._set_size(node, 0, v))
            sh.valueChanged.connect(lambda v: self._set_size(node, 1, v))
            color = self._color_button(node.color, lambda c: self._set_color(node, c))
            f.addRow('Width', sw)
            f.addRow('Height', sh)
            f.addRow('Color', color)
            self._layout.addWidget(g)
        if isinstance(node, Sprite2D):
            g = QGroupBox('Sprite2D')
            f = QFormLayout(g)
            tex = QLineEdit(node.texture_path)
            tr = QHBoxLayout()
            tr.addWidget(tex, 1)
            b = QPushButton('…')
            b.setFixedWidth(30)
            b.clicked.connect(lambda: self._pick_texture(tex))
            tr.addWidget(b)
            tex.editingFinished.connect(lambda: self._set_attr('texture_path', tex.text().strip().replace('\\', '/')))
            centered = self._check(node.centered, lambda v: self._set_attr('centered', v))
            fh = self._check(node.flip_h, lambda v: self._set_attr('flip_h', v))
            fv = self._check(node.flip_v, lambda v: self._set_attr('flip_v', v))
            op = self._float(node.opacity, 0, 1)
            op.setSingleStep(0.05)
            op.valueChanged.connect(lambda v: self._set_attr('opacity', v))
            f.addRow('Texture', tr)
            f.addRow('Centered', centered)
            f.addRow('Flip H', fh)
            f.addRow('Flip V', fv)
            f.addRow('Opacity', op)
            self._layout.addWidget(g)
        if isinstance(node, Label2D):
            g = QGroupBox('Label2D')
            f = QFormLayout(g)
            text = QLineEdit(node.text)
            text.editingFinished.connect(lambda: self._set_attr('text', text.text()))
            fs = QSpinBox()
            fs.setRange(6, 512)
            fs.setValue(node.font_size)
            fs.valueChanged.connect(lambda v: self._set_attr('font_size', v))
            color = self._color_button(node.color, lambda c: self._set_color(node, c))
            f.addRow('Text', text)
            f.addRow('Font Size', fs)
            f.addRow('Color', color)
            self._layout.addWidget(g)
        if isinstance(node, Camera2DNode):
            g = QGroupBox('Camera2D')
            f = QFormLayout(g)
            cur = self._check(node.current, lambda v: self._set_attr('current', v))
            zoom = self._float(node.zoom, 0.01, 100)
            zoom.valueChanged.connect(lambda v: self._set_attr('zoom', v))
            f.addRow('Current', cur)
            f.addRow('Zoom', zoom)
            self._layout.addWidget(g)
        if isinstance(node, CollisionRect2D):
            g = QGroupBox('CollisionRect2D')
            f = QFormLayout(g)
            sw = self._float(node.size.x, 1, 100000)
            sh = self._float(node.size.y, 1, 100000)
            sw.valueChanged.connect(lambda v: self._set_size(node, 0, v))
            sh.valueChanged.connect(lambda v: self._set_size(node, 1, v))
            trig = self._check(node.is_trigger, lambda v: self._set_attr('is_trigger', v))
            dbg = self._check(node.debug_visible, lambda v: self._set_attr('debug_visible', v))
            f.addRow('Width', sw)
            f.addRow('Height', sh)
            f.addRow('Trigger', trig)
            f.addRow('Debug Draw', dbg)
            self._layout.addWidget(g)
        if isinstance(node, Timer):
            g = QGroupBox('Timer')
            f = QFormLayout(g)
            wait = self._float(node.wait_time, 0.001, 100000)
            wait.valueChanged.connect(lambda v: self._set_attr('wait_time', v))
            one = self._check(node.one_shot, lambda v: self._set_attr('one_shot', v))
            auto = self._check(node.autostart, lambda v: self._set_attr('autostart', v))
            paused = self._check(node.paused, lambda v: self._set_attr('paused', v))
            f.addRow('Wait Time', wait)
            f.addRow('One Shot', one)
            f.addRow('Autostart', auto)
            f.addRow('Paused', paused)
            self._layout.addWidget(g)
        if isinstance(node, AudioStreamPlayer2D):
            g = QGroupBox('Audio Stream')
            f = QFormLayout(g)
            stream = QLineEdit(node.stream_path)
            stream.editingFinished.connect(lambda: self._set_attr('stream_path', stream.text().strip().replace('\\', '/')))
            auto = self._check(node.autoplay, lambda v: self._set_attr('autoplay', v))
            loop = self._check(node.loop, lambda v: self._set_attr('loop', v))
            vol = self._float(node.volume, 0, 1)
            vol.setSingleStep(0.05)
            vol.valueChanged.connect(lambda v: self._set_attr('volume', v))
            f.addRow('Stream', stream)
            f.addRow('Autoplay', auto)
            f.addRow('Loop', loop)
            f.addRow('Volume', vol)
            self._layout.addWidget(g)
        if isinstance(node, Button2D):
            g = QGroupBox('Button2D')
            f = QFormLayout(g)
            text = QLineEdit(node.text)
            text.editingFinished.connect(lambda: self._set_attr('text', text.text()))
            sw = self._float(node.size.x, 1, 10000)
            sh = self._float(node.size.y, 1, 10000)
            sw.valueChanged.connect(lambda v: self._set_size(node, 0, v))
            sh.valueChanged.connect(lambda v: self._set_size(node, 1, v))
            disabled = self._check(node.disabled, lambda v: self._set_attr('disabled', v))
            screen = self._check(node.screen_space, lambda v: self._set_attr('screen_space', v))
            f.addRow('Text', text)
            f.addRow('Width', sw)
            f.addRow('Height', sh)
            f.addRow('Disabled', disabled)
            f.addRow('Screen Space', screen)
            self._layout.addWidget(g)
        if isinstance(node, TileMap2D):
            g = QGroupBox('TileMap2D')
            f = QFormLayout(g)
            tex = QLineEdit(node.texture_path)
            tex.editingFinished.connect(lambda: self._set_attr('texture_path', tex.text().strip().replace('\\', '/')))
            tw = self._float(node.tile_size.x, 1, 4096)
            th = self._float(node.tile_size.y, 1, 4096)
            tw.valueChanged.connect(lambda v: self._set_tile_size(0, v))
            th.valueChanged.connect(lambda v: self._set_tile_size(1, v))
            cols = QSpinBox()
            cols.setRange(1, 4096)
            cols.setValue(node.atlas_columns)
            cols.valueChanged.connect(lambda v: self._set_attr('atlas_columns', v))
            dbg = self._check(node.debug_grid, lambda v: self._set_attr('debug_grid', v))
            f.addRow('Atlas', tex)
            f.addRow('Tile W', tw)
            f.addRow('Tile H', th)
            f.addRow('Columns', cols)
            f.addRow('Debug Grid', dbg)
            f.addRow('Cells', QLabel(str(len(node.tiles))))
            self._layout.addWidget(g)
        if isinstance(node, ParticleSystem2D):
            g = QGroupBox('ParticleSystem2D')
            f = QFormLayout(g)
            emit = self._check(node.emitting, lambda v: self._set_attr('emitting', v))
            amt = QSpinBox()
            amt.setRange(0, 100000)
            amt.setValue(node.amount)
            amt.valueChanged.connect(lambda v: self._set_attr('amount', v))
            rate = self._float(node.emission_rate, 0, 100000)
            rate.valueChanged.connect(lambda v: self._set_attr('emission_rate', v))
            life = self._float(node.lifetime, 0.01, 1000)
            life.valueChanged.connect(lambda v: self._set_attr('lifetime', v))
            smin = self._float(node.speed_min, -100000, 100000)
            smax = self._float(node.speed_max, -100000, 100000)
            smin.valueChanged.connect(lambda v: self._set_attr('speed_min', v))
            smax.valueChanged.connect(lambda v: self._set_attr('speed_max', v))
            spread = self._float(node.spread, 0, 360)
            spread.valueChanged.connect(lambda v: self._set_attr('spread', v))
            f.addRow('Emitting', emit)
            f.addRow('Amount', amt)
            f.addRow('Rate', rate)
            f.addRow('Lifetime', life)
            f.addRow('Speed Min', smin)
            f.addRow('Speed Max', smax)
            f.addRow('Spread °', spread)
            self._layout.addWidget(g)
        if isinstance(node, Control):
            g = QGroupBox('UI Layout / Anchors')
            f = QFormLayout(g)
            preset = QComboBox()
            preset.addItems(['top_left', 'top_right', 'bottom_left', 'bottom_right', 'center', 'full_rect', 'top_wide', 'bottom_wide'])
            preset.currentTextChanged.connect(lambda v: self._set_anchor_preset(v))
            f.addRow('Anchor Preset', preset)
            for attr, label in (('anchor_left', 'Left Anchor'), ('anchor_top', 'Top Anchor'), ('anchor_right', 'Right Anchor'), ('anchor_bottom', 'Bottom Anchor'), ('offset_left', 'Left Offset'), ('offset_top', 'Top Offset'), ('offset_right', 'Right Offset'), ('offset_bottom', 'Bottom Offset')):
                w = self._float(getattr(node, attr), -100000, 100000)
                w.valueChanged.connect(lambda v, a=attr: self._set_attr(a, v))
                f.addRow(label, w)
            self._layout.addWidget(g)
        if isinstance(node, Light2D):
            g = QGroupBox('Light2D')
            f = QFormLayout(g)
            rad = self._float(node.radius, 1, 100000)
            rad.valueChanged.connect(lambda v: self._set_attr('radius', v))
            energy = self._float(node.energy, 0, 20)
            energy.valueChanged.connect(lambda v: self._set_attr('energy', v))
            soft = self._float(node.softness, 0, 1)
            soft.valueChanged.connect(lambda v: self._set_attr('softness', v))
            enabled = self._check(node.enabled, lambda v: self._set_attr('enabled', v))
            color = self._color_button(node.color, lambda c: self._set_color(node, c))
            f.addRow('Radius', rad)
            f.addRow('Energy', energy)
            f.addRow('Softness', soft)
            f.addRow('Enabled', enabled)
            f.addRow('Color', color)
            self._layout.addWidget(g)
        if isinstance(node, Navigation2D):
            g = QGroupBox('Navigation2D')
            f = QFormLayout(g)
            cell = self._float(node.cell_size, 1, 10000)
            cell.valueChanged.connect(lambda v: self._set_attr('cell_size', v))
            w = QSpinBox()
            w.setRange(1, 10000)
            w.setValue(node.width)
            w.valueChanged.connect(lambda v: self._set_attr('width', v))
            h = QSpinBox()
            h.setRange(1, 10000)
            h.setValue(node.height)
            h.valueChanged.connect(lambda v: self._set_attr('height', v))
            diag = self._check(node.allow_diagonal, lambda v: self._set_attr('allow_diagonal', v))
            dbg = self._check(node.debug_visible, lambda v: self._set_attr('debug_visible', v))
            f.addRow('Cell Size', cell)
            f.addRow('Width', w)
            f.addRow('Height', h)
            f.addRow('Diagonal', diag)
            f.addRow('Debug', dbg)
            f.addRow('Blocked Cells', QLabel(str(len(node.blocked))))
            self._layout.addWidget(g)
        if isinstance(node, NavigationAgent2D):
            g = QGroupBox('NavigationAgent2D')
            f = QFormLayout(g)
            tx = self._float(node.target_position.x)
            ty = self._float(node.target_position.y)
            tx.valueChanged.connect(lambda v: self._set_target(0, v))
            ty.valueChanged.connect(lambda v: self._set_target(1, v))
            speed = self._float(node.speed, 0, 100000)
            speed.valueChanged.connect(lambda v: self._set_attr('speed', v))
            f.addRow('Target X', tx)
            f.addRow('Target Y', ty)
            f.addRow('Speed', speed)
            self._layout.addWidget(g)
        if isinstance(node, PhysicsBody2D):
            g = QGroupBox('Physics Body')
            f = QFormLayout(g)
            mass = self._float(node.mass, 0.001, 100000)
            grav = self._float(node.gravity_scale, -1000, 1000)
            rest = self._float(node.restitution, 0, 1)
            fric = self._float(node.friction, 0, 10)
            mass.valueChanged.connect(lambda v: self._set_attr('mass', v))
            grav.valueChanged.connect(lambda v: self._set_attr('gravity_scale', v))
            rest.valueChanged.connect(lambda v: self._set_attr('restitution', v))
            fric.valueChanged.connect(lambda v: self._set_attr('friction', v))
            cw = self._float(node.collider.size.x, 1, 100000)
            ch = self._float(node.collider.size.y, 1, 100000)
            cw.valueChanged.connect(lambda v: self._set_collider_size(0, v))
            ch.valueChanged.connect(lambda v: self._set_collider_size(1, v))
            trigger = self._check(node.collider.is_trigger, lambda v: self._set_collider('is_trigger', v))
            cl = QSpinBox()
            cl.setRange(1, 2147483647)
            cl.setValue(int(getattr(node, 'collision_layer', 1)))
            cl.valueChanged.connect(lambda v: self._set_attr('collision_layer', v))
            cm = QSpinBox()
            cm.setRange(0, 2147483647)
            cm.setValue(min(2147483647, int(getattr(node, 'collision_mask', 2147483647))))
            cm.valueChanged.connect(lambda v: self._set_attr('collision_mask', v))
            f.addRow('Body Type', QLabel(node.body_type.name))
            f.addRow('Mass', mass)
            f.addRow('Gravity Scale', grav)
            f.addRow('Restitution', rest)
            f.addRow('Friction', fric)
            f.addRow('Collider W', cw)
            f.addRow('Collider H', ch)
            f.addRow('Trigger', trigger)
            f.addRow('Collision Layer Bits', cl)
            f.addRow('Collision Mask Bits', cm)
            self._layout.addWidget(g)
        self._layout.addStretch(1)

    def _float(self, value: float, minimum: float=-100000, maximum: float=100000) -> QDoubleSpinBox:
        b = QDoubleSpinBox()
        b.setDecimals(3)
        b.setRange(minimum, maximum)
        b.setSingleStep(1)
        b.setValue(value)
        return b

    def _check(self, value: bool, slot) -> QCheckBox:
        c = QCheckBox()
        c.setChecked(value)
        c.toggled.connect(slot)
        return c

    def _color_button(self, color, slot) -> QPushButton:
        b = QPushButton(f'RGB {tuple(color)}')

        def pick():
            q = QColorDialog.getColor(QColor(*color), self, 'Choose Color')
            if q.isValid():
                slot((q.red(), q.green(), q.blue()))
                b.setText(f'RGB {(q.red(), q.green(), q.blue())}')
        b.clicked.connect(pick)
        return b

    def _changed(self) -> None:
        if self._node is not None:
            self.property_changed.emit(self._node)

    def _set_name(self, value: str) -> None:
        if self._node is not None and value.strip():
            self._node.name = value.strip()
            self._changed()

    def _set_attr(self, name: str, value) -> None:
        if self._node is not None:
            setattr(self._node, name, value)
            self._changed()

    def _set_int_text_attr(self, name: str, text: str, default: int=0) -> None:
        try:
            value = int(str(text).strip(), 0)
        except ValueError:
            value = int(default)
        self._set_attr(name, value & 0xFFFFFFFF)

    def _set_camera_current(self, value: bool) -> None:
        if isinstance(self._node, Camera3DNode):
            if value:
                self._node.make_current()
            else:
                self._node.clear_current()
            self._changed()

    def _set_vec(self, name: str, index: int, value: float) -> None:
        if not isinstance(self._node, Node2D):
            return
        v = getattr(self._node, name)
        v.x = value if index == 0 else v.x
        v.y = value if index == 1 else v.y
        self._changed()

    def _set_vec3(self, name: str, index: int, value: float) -> None:
        if not isinstance(self._node, Node3D):
            return
        v = getattr(self._node, name)
        if index == 0:
            v.x = value
        elif index == 1:
            v.y = value
        else:
            v.z = value
        self._changed()

    def _set_size3d(self, index: int, value: float) -> None:
        if isinstance(self._node, MeshInstance3D):
            if index == 0:
                self._node.size.x = value
            elif index == 1:
                self._node.size.y = value
            else:
                self._node.size.z = value
            self._changed()

    def _set_size(self, node, index: int, value: float) -> None:
        if hasattr(node, 'size'):
            if index == 0:
                node.size.x = value
            else:
                node.size.y = value
            self._changed()

    def _set_color(self, node, color) -> None:
        node.color = tuple(color)
        self._changed()

    def _set_collider3d_size(self, index: int, value: float) -> None:
        if isinstance(self._node, PhysicsBody3D):
            if index == 0:
                self._node.collider.size.x = value
            elif index == 1:
                self._node.collider.size.y = value
            else:
                self._node.collider.size.z = value
            self._changed()

    def _set_collider3d(self, name: str, value) -> None:
        if isinstance(self._node, PhysicsBody3D):
            setattr(self._node.collider, name, value)
            self._changed()

    def _set_collider_size(self, index: int, value: float) -> None:
        if isinstance(self._node, PhysicsBody2D):
            if index == 0:
                self._node.collider.size.x = value
            else:
                self._node.collider.size.y = value
            self._changed()

    def _set_collider(self, name: str, value) -> None:
        if isinstance(self._node, PhysicsBody2D):
            setattr(self._node.collider, name, value)
            self._changed()

    def _set_groups(self, text: str) -> None:
        if self._node is not None:
            self._node.groups = {x.strip() for x in text.split(',') if x.strip()}
            self._changed()

    def _set_tile_size(self, index: int, value: float) -> None:
        if isinstance(self._node, TileMap2D):
            if index == 0:
                self._node.tile_size.x = value
            else:
                self._node.tile_size.y = value
            self._changed()

    def _set_target(self, index: int, value: float) -> None:
        if isinstance(self._node, NavigationAgent2D):
            if index == 0:
                self._node.target_position.x = value
            else:
                self._node.target_position.y = value
            self._changed()

    def _set_anchor_preset(self, preset: str) -> None:
        if isinstance(self._node, Control):
            self._node.set_anchor_preset(preset)
            self._changed()

    def _pick_mesh3d(self, edit: QLineEdit) -> None:
        path, _ = QFileDialog.getOpenFileName(self, 'Choose 3D Mesh', str(self.project_dir / 'assets'), '3D Mesh (*.obj *.stl)')
        if path:
            try:
                path = Path(path).resolve().relative_to(self.project_dir).as_posix()
            except ValueError:
                pass
            edit.setText(str(path))
            self._set_attr('mesh_path', str(path))

    def _pick_material(self, edit: QLineEdit) -> None:
        path, _ = QFileDialog.getOpenFileName(self, 'Choose Material', str(self.project_dir / 'assets' / 'materials'), 'V Works Material (*.vmat)')
        if path:
            try:
                path = Path(path).resolve().relative_to(self.project_dir).as_posix()
            except ValueError:
                pass
            edit.setText(str(path))
            self._set_attr('material_path', str(path))

    def _pick_texture(self, edit: QLineEdit) -> None:
        path, _ = QFileDialog.getOpenFileName(self, 'Choose Texture', str(self.project_dir / 'assets'), 'Images (*.png *.jpg *.jpeg *.bmp *.webp)')
        if path:
            try:
                path = Path(path).resolve().relative_to(self.project_dir).as_posix()
            except ValueError:
                pass
            edit.setText(str(path))
            self._set_attr('texture_path', str(path))

    def _pick_script(self, edit: QLineEdit) -> None:
        path, _ = QFileDialog.getOpenFileName(self, 'Attach Python Script', str(self.project_dir / 'scripts'), 'Python (*.py)')
        if path:
            try:
                path = Path(path).resolve().relative_to(self.project_dir).as_posix()
            except ValueError:
                pass
            edit.setText(str(path))
            self._set_attr('script_path', str(path))

    def _open_script(self, text: str) -> None:
        if text.strip():
            self.script_open_requested.emit(text.strip())
