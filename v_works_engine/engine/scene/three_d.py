from __future__ import annotations
from ..utils.vmath import Vector3, rotate_euler
from .node import Node3D

class MeshInstance3D(Node3D):
    def __init__(self, name: str='MeshInstance3D', primitive: str='cube') -> None:
        super().__init__(name)
        self.primitive = primitive
        self.mesh_path = ''
        self.size = Vector3(1.0, 1.0, 1.0)
        self.color = (110, 170, 235)
        self.wireframe = False
        self.shaded = True
        self.double_sided = True
        self.segments = 14
        self.rings = 9
        self.cast_shadow = True
        self.receive_light = True

    def _draw(self, renderer) -> None:
        if self.visible and hasattr(renderer, 'queue_mesh_3d'):
            renderer.queue_mesh_3d(self)

class Camera3DNode(Node3D):
    def __init__(self, name: str='Camera3D') -> None:
        super().__init__(name)
        self.current = True
        self.fov = 70.0
        self.near = 0.05
        self.far = 2000.0
        self.orthographic = False
        self.ortho_size = 10.0
        self.cull_mask = 0xFFFFFFFF

    def make_current(self) -> None:
        root = self
        while root.parent is not None:
            root = root.parent
        for node in root.walk():
            if isinstance(node, Camera3DNode):
                node.current = node is self

    def clear_current(self) -> None:
        self.current = False

    def sync_renderer(self, renderer) -> None:
        camera = getattr(renderer, 'camera3d', None) if renderer else None
        if camera is None:
            return
        camera.enabled = bool(self.current)
        camera.position = self.global_position
        camera.rotation = self.global_rotation
        camera.fov = max(1.0, min(179.0, float(self.fov)))
        camera.near = max(0.001, float(self.near))
        camera.far = max(camera.near + 0.001, float(self.far))
        camera.orthographic = bool(self.orthographic)
        camera.ortho_size = max(0.01, float(self.ortho_size))
        camera.cull_mask = int(self.cull_mask) & 0xFFFFFFFF
        camera.source_node = self

    def _process(self, delta: float) -> None:
        if not self.current:
            return
        tree = self.get_tree()
        engine = getattr(tree, 'engine', None) if tree else None
        renderer = getattr(engine, 'renderer', None) if engine else None
        if renderer is not None:
            self.sync_renderer(renderer)

class DirectionalLight3D(Node3D):
    def __init__(self, name: str='DirectionalLight3D') -> None:
        super().__init__(name)
        self.color = (255, 244, 220)
        self.energy = 1.0
        self.ambient = 0.22
        self.enabled = True

    @property
    def direction(self) -> Vector3:
        return self.global_forward

    def _process(self, delta: float) -> None:
        if not self.enabled:
            return
        tree = self.get_tree()
        engine = getattr(tree, 'engine', None) if tree else None
        renderer = getattr(engine, 'renderer', None) if engine else None
        if renderer is not None and hasattr(renderer, 'set_directional_light_3d'):
            renderer.set_directional_light_3d(self.direction, self.color, self.energy, self.ambient)

class PointLight3D(Node3D):
    def __init__(self, name: str='PointLight3D') -> None:
        super().__init__(name)
        self.color = (255, 220, 170)
        self.energy = 1.0
        self.range = 8.0
        self.attenuation = 2.0
        self.enabled = True

class SpotLight3D(PointLight3D):
    def __init__(self, name: str='SpotLight3D') -> None:
        super().__init__(name)
        self.spot_angle = 45.0
        self.edge_softness = 0.2

    @property
    def direction(self) -> Vector3:
        return self.global_forward

class WorldEnvironment3D(Node3D):
    def __init__(self, name: str='WorldEnvironment3D') -> None:
        super().__init__(name)
        self.ambient_color = (255, 255, 255)
        self.ambient_energy = 0.22
        self.fog_enabled = False
        self.fog_color = (100, 120, 145)
        self.fog_near = 20.0
        self.fog_far = 100.0
        self.sky_enabled = False
        self.sky_top_color = (35, 50, 82)
        self.sky_bottom_color = (145, 185, 225)

    def _process(self, delta: float) -> None:
        tree = self.get_tree()
        engine = getattr(tree, 'engine', None) if tree else None
        renderer = getattr(engine, 'renderer', None) if engine else None
        if renderer is not None and hasattr(renderer, 'set_environment_3d'):
            renderer.set_environment_3d(
                self.ambient_color,
                self.ambient_energy,
                self.fog_enabled,
                self.fog_color,
                self.fog_near,
                self.fog_far,
                self.sky_enabled,
                self.sky_top_color,
                self.sky_bottom_color,
            )

class Marker3D(Node3D):
    def __init__(self, name: str='Marker3D') -> None:
        super().__init__(name)

class RayCast3D(Node3D):
    def __init__(self, name: str='RayCast3D') -> None:
        super().__init__(name)
        self.target_position = Vector3(0.0, 0.0, -5.0)
        self.enabled = True
        self.collision_mask = 0xFFFFFFFF
        self.exclude_parent = True
        self.colliding = False
        self.collider = None
        self.collision_point = Vector3()
        self.collision_normal = Vector3()
        self.signals.add('hit_changed')

    def force_raycast_update(self) -> bool:
        tree = self.get_tree()
        engine = getattr(tree, 'engine', None) if tree else None
        physics = getattr(engine, 'physics', None) if engine else None
        if not self.enabled or physics is None or tree is None or not hasattr(physics, 'raycast_3d'):
            self._set_hit(None)
            return False
        start = self.global_position
        end = self.to_global(self.target_position)
        exclude = {self}
        if self.exclude_parent and self.parent is not None:
            exclude.add(self.parent)
        hit = physics.raycast_3d(tree.root, start, end, self.collision_mask, exclude)
        self._set_hit(hit)
        return self.colliding

    def _set_hit(self, hit) -> None:
        previous = self.collider
        if hit:
            self.colliding = True
            self.collider = hit['body']
            self.collision_point = hit['point']
            self.collision_normal = hit['normal']
        else:
            self.colliding = False
            self.collider = None
            self.collision_point = Vector3()
            self.collision_normal = Vector3()
        if previous is not self.collider:
            self.signals.emit('hit_changed', self.collider)

    def _physics_process(self, delta: float) -> None:
        if self.enabled:
            self.force_raycast_update()
