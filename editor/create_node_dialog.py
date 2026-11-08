from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QLineEdit, QListWidget, QListWidgetItem, QVBoxLayout
NODE_CATALOG = [('Node', 'Core', 'Base scene object with groups, tag/layer, signals and Python script.'), ('Node2D', '2D', '2D transform: position / rotation / scale / material.'), ('Node3D', '3D', '3D transform node with position, Euler rotation and scale.'), ('MeshInstance3D', '3D', 'Software-rendered 3D primitive mesh: cube, sphere, plane, pyramid or cylinder.'), ('Camera3D', '3D', 'Perspective or orthographic 3D runtime camera.'), ('DirectionalLight3D', '3D / Lighting', 'Directional sun-style light for shaded 3D meshes.'), ('PointLight3D', '3D / Lighting', 'Local omnidirectional point light with range and attenuation.'), ('SpotLight3D', '3D / Lighting', 'Cone light with range, angle and edge softness.'), ('WorldEnvironment3D', '3D / Environment', 'Ambient light, fog and optional sky gradient for 3D scenes.'), ('Marker3D', '3D / Utility', 'Transform marker for spawn points, targets and sockets.'), ('RayCast3D', '3D / Physics', 'Segment ray query against 3D AABB physics bodies.'), ('StaticBody3D', '3D / Physics', 'Immovable 3D AABB physics body.'), ('RigidBody3D', '3D / Physics', 'Gravity-driven 3D AABB physics body.'), ('CharacterBody3D', '3D / Physics', 'Script-controlled 3D character body.'), ('Area3D', '3D / Physics', 'Godot-style trigger volume with body_entered/body_exited signals.'), ('Sprite2D', '2D', 'Image sprite with material/shader resource support.'), ('ColorRect2D', '2D', 'Fast colored rectangle for prototypes and backgrounds.'), ('Label2D', '2D', 'World-space text label.'), ('Camera2D', '2D', 'Runtime camera with position and zoom.'), ('TileMap2D', '2D / Tile', 'Atlas tile map with editor TileMap panel.'), ('ParticleSystem2D', '2D / VFX', 'CPU particle emitter with lifetime, gravity, speed and color.'), ('Light2D', '2D / Lighting', 'Additive radial 2D light.'), ('CanvasModulate', '2D / Lighting', 'Global canvas tint/modulation node.'), ('Navigation2D', 'Navigation', 'A* grid navigation region with blocked cells.'), ('NavigationAgent2D', 'Navigation', 'Agent that follows a Navigation2D path.'), ('StaticBody2D', 'Physics', 'Immovable AABB physics body.'), ('RigidBody2D', 'Physics', 'Gravity/force-driven physics body.'), ('CharacterBody2D', 'Physics', 'Script-controlled kinematic body.'), ('Area2D', 'Physics', 'Trigger area with body_entered/body_exited signals.'), ('CollisionRect2D', 'Physics', 'Rectangle collider helper; place under a body.'), ('CanvasLayer', 'UI', 'Screen UI hierarchy root.'), ('Control', 'UI', 'Anchored UI control with offsets.'), ('UIPanel', 'UI', 'Anchored translucent panel.'), ('UILabel', 'UI', 'Anchored screen-space text.'), ('Button2D', 'UI', 'Clickable runtime UI button with pressed signal.'), ('Timer', 'Utility', 'Godot-style timer with timeout signal.'), ('AudioStreamPlayer2D', 'Audio', 'Play sound/music with autoplay, loop and volume.')]

NODE_CATALOG += [
    ('Path3D', '3D / Utility', 'Editable polyline of Vector3 points for motion paths.'),
    ('PathFollow3D', '3D / Utility', 'Move children along a Path3D with progress, speed and looping.'),
    ('LookAt3D', '3D / Utility', 'Automatically orient an object toward another Node3D.'),
]

NODE_CATALOG += [('UICanvas','UI','Reference-resolution canvas with letterboxing.'),
                 ('UIImage','UI','Authored image, tint and fill amount.'),
                 ('UIButton','UI','Anchored button supporting mouse and touch.'),
                 ('VideoPlayer','Media','Seekable V-Works video clip, updated by SceneTree.')]

class CreateNodeDialog(QDialog):

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle('Create New Node')
        self.resize(590, 500)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel('Search node type'))
        self.search = QLineEdit()
        self.search.setPlaceholderText('Sprite2D, MeshInstance3D, Camera3D, RigidBody2D…')
        layout.addWidget(self.search)
        self.list = QListWidget()
        layout.addWidget(self.list, 1)
        self.description = QLabel()
        self.description.setWordWrap(True)
        layout.addWidget(self.description)
        buttons = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.search.textChanged.connect(self._rebuild)
        self.list.currentItemChanged.connect(self._selection_changed)
        self.list.itemDoubleClicked.connect(lambda _: self.accept())
        self._rebuild()
        self.search.setFocus(Qt.OtherFocusReason)

    def _rebuild(self) -> None:
        query = self.search.text().strip().lower()
        self.list.clear()
        for type_name, category, description in NODE_CATALOG:
            if query and query not in f'{type_name} {category} {description}'.lower():
                continue
            item = QListWidgetItem(f'{type_name:<22} {category}')
            item.setData(Qt.UserRole, (type_name, description))
            self.list.addItem(item)
        if self.list.count():
            self.list.setCurrentRow(0)

    def _selection_changed(self, item, previous) -> None:
        if item is None:
            self.description.clear()
            return
        type_name, desc = item.data(Qt.UserRole)
        self.description.setText(f'<b>{type_name}</b><br>{desc}')

    def selected_type(self) -> str | None:
        item = self.list.currentItem()
        return item.data(Qt.UserRole)[0] if item else None
