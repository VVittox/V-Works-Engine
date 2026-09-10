from __future__ import annotations
import copy
import json
import os
from pathlib import Path
from typing import Any, Dict
from .node import Node, Node2D, Node3D
from .scene import Scene
from .shapes import Camera2DNode, CollisionRect2D, ColorRect2D, Label2D, Sprite2D
from .runtime_nodes import Timer, AudioStreamPlayer2D, Button2D
from .advanced_nodes import CanvasLayer, CanvasModulate, Control, Light2D, Navigation2D, NavigationAgent2D, ParticleSystem2D, TileMap2D, UILabel, UIPanel
from .three_d import MeshInstance3D, Camera3DNode, DirectionalLight3D, PointLight3D, SpotLight3D, WorldEnvironment3D, Marker3D, RayCast3D
from ..physics.body import BodyType, CharacterBody2D, PhysicsBody2D, RigidBody2D, StaticBody2D, Area2D
from ..physics.body3d import CharacterBody3D, PhysicsBody3D, RigidBody3D, StaticBody3D, Area3D
from ..utils.vmath import Vector2, Vector3
SCENE_VERSION = 5
NODE_TYPES = {'Node': Node, 'Node2D': Node2D, 'Node3D': Node3D, 'Scene': Scene, 'ColorRect2D': ColorRect2D, 'Sprite2D': Sprite2D, 'Label2D': Label2D, 'Camera2DNode': Camera2DNode, 'Camera2D': Camera2DNode, 'CollisionRect2D': CollisionRect2D, 'PhysicsBody2D': PhysicsBody2D, 'StaticBody2D': StaticBody2D, 'RigidBody2D': RigidBody2D, 'CharacterBody2D': CharacterBody2D, 'Area2D': Area2D, 'PhysicsBody3D': PhysicsBody3D, 'StaticBody3D': StaticBody3D, 'RigidBody3D': RigidBody3D, 'CharacterBody3D': CharacterBody3D, 'Area3D': Area3D, 'Timer': Timer, 'AudioStreamPlayer2D': AudioStreamPlayer2D, 'Button2D': Button2D, 'TileMap2D': TileMap2D, 'ParticleSystem2D': ParticleSystem2D, 'CanvasLayer': CanvasLayer, 'Control': Control, 'UIPanel': UIPanel, 'UILabel': UILabel, 'Light2D': Light2D, 'CanvasModulate': CanvasModulate, 'Navigation2D': Navigation2D, 'NavigationAgent2D': NavigationAgent2D, 'MeshInstance3D': MeshInstance3D, 'Camera3DNode': Camera3DNode, 'Camera3D': Camera3DNode, 'DirectionalLight3D': DirectionalLight3D, 'PointLight3D': PointLight3D, 'SpotLight3D': SpotLight3D, 'WorldEnvironment3D': WorldEnvironment3D, 'Marker3D': Marker3D, 'RayCast3D': RayCast3D}

def _v2(v: Vector2) -> list[float]:
    return [v.x, v.y]

def _vec(value: Any, default=(0.0, 0.0)) -> Vector2:
    value = value if isinstance(value, (list, tuple)) and len(value) >= 2 else default
    return Vector2(float(value[0]), float(value[1]))

def _v3(v: Vector3) -> list[float]:
    return [v.x, v.y, v.z]

def _vec3(value: Any, default=(0.0, 0.0, 0.0)) -> Vector3:
    value = value if isinstance(value, (list, tuple)) and len(value) >= 3 else default
    return Vector3(float(value[0]), float(value[1]), float(value[2]))

def node_to_dict(node: Node) -> Dict[str, Any]:
    data: Dict[str, Any] = {'type': node.__class__.__name__, 'name': node.name, 'script': getattr(node, 'script_path', ''), 'groups': sorted(getattr(node, 'groups', set())), 'tag': getattr(node, 'tag', 'Untagged'), 'layer': int(getattr(node, 'layer', 0)), 'signal_connections': copy.deepcopy(getattr(node, 'signal_connections', [])), 'editor_locked': bool(getattr(node, 'editor_locked', False)), 'children': [node_to_dict(child) for child in node.get_children()]}
    if isinstance(node, Node2D):
        data.update({'position': _v2(node.position), 'rotation': node.rotation, 'scale': _v2(node.scale), 'visible': node.visible, 'z_index': node.z_index, 'material': getattr(node, 'material_path', '')})
    if isinstance(node, Node3D):
        data.update({'position3d': _v3(node.position), 'rotation3d': _v3(node.rotation), 'scale3d': _v3(node.scale), 'visible3d': node.visible, 'render_layer': node.render_layer, 'material3d': getattr(node, 'material_path', '')})
    if isinstance(node, ColorRect2D):
        data.update({'size': _v2(node.size), 'color': list(node.color)})
    if isinstance(node, Sprite2D):
        data.update({'texture': node.texture_path, 'centered': node.centered, 'flip_h': node.flip_h, 'flip_v': node.flip_v, 'opacity': node.opacity})
    if isinstance(node, Label2D):
        data.update({'text': node.text, 'font_size': node.font_size, 'color': list(node.color), 'font_path': node.font_path})
    if isinstance(node, Camera2DNode):
        data.update({'current': node.current, 'camera_zoom': node.zoom})
    if isinstance(node, CollisionRect2D):
        data.update({'size': _v2(node.size), 'is_trigger': node.is_trigger, 'debug_visible': node.debug_visible})
    if isinstance(node, PhysicsBody2D):
        data.update({'body_type': node.body_type.name, 'velocity': _v2(node.velocity), 'mass': node.mass, 'gravity_scale': node.gravity_scale, 'restitution': node.restitution, 'friction': node.friction, 'collider_size': _v2(node.collider.size), 'collider_offset': _v2(node.collider.offset), 'collider_enabled': node.collider.enabled, 'collider_trigger': node.collider.is_trigger, 'collision_layer': int(getattr(node, 'collision_layer', 1)), 'collision_mask': int(getattr(node, 'collision_mask', 4294967295))})
    if isinstance(node, PhysicsBody3D):
        data.update({'body_type3d': node.body_type.name, 'velocity3d': _v3(node.velocity), 'mass3d': node.mass, 'gravity_scale3d': node.gravity_scale, 'restitution3d': node.restitution, 'friction3d': node.friction, 'collider_size3d': _v3(node.collider.size), 'collider_offset3d': _v3(node.collider.offset), 'collider_enabled3d': node.collider.enabled, 'collider_trigger3d': node.collider.is_trigger, 'collision_layer3d': int(getattr(node, 'collision_layer', 1)), 'collision_mask3d': int(getattr(node, 'collision_mask', 4294967295))})
    if isinstance(node, Timer):
        data.update({'wait_time': node.wait_time, 'one_shot': node.one_shot, 'autostart': node.autostart, 'paused': node.paused})
    if isinstance(node, AudioStreamPlayer2D):
        data.update({'stream': node.stream_path, 'autoplay': node.autoplay, 'loop': node.loop, 'volume': node.volume})
    if isinstance(node, Button2D):
        data.update({'text': node.text, 'size': _v2(node.size), 'color': list(node.color), 'hover_color': list(node.hover_color), 'text_color': list(node.text_color), 'disabled': node.disabled, 'screen_space': node.screen_space})
    if isinstance(node, TileMap2D):
        data.update({'texture': node.texture_path, 'tile_size': _v2(node.tile_size), 'atlas_columns': node.atlas_columns, 'margin': node.margin, 'spacing': node.spacing, 'tiles': dict(node.tiles), 'collision_tiles': sorted(node.collision_tiles), 'debug_grid': node.debug_grid})
    if isinstance(node, ParticleSystem2D):
        data.update({'emitting': node.emitting, 'amount': node.amount, 'emission_rate': node.emission_rate, 'lifetime': node.lifetime, 'speed_min': node.speed_min, 'speed_max': node.speed_max, 'direction': node.direction, 'spread': node.spread, 'gravity': _v2(node.gravity), 'color_start': list(node.color_start), 'color_end': list(node.color_end), 'size_start': node.size_start, 'size_end': node.size_end, 'texture': node.texture_path, 'local_coords': node.local_coords})
    if isinstance(node, CanvasLayer):
        data.update({'canvas_layer': node.layer, 'canvas_visible': node.visible})
    if isinstance(node, Control):
        data.update({'size': _v2(node.size), 'anchors': [node.anchor_left, node.anchor_top, node.anchor_right, node.anchor_bottom], 'offsets': [node.offset_left, node.offset_top, node.offset_right, node.offset_bottom], 'mouse_filter': node.mouse_filter})
    if isinstance(node, UIPanel):
        data.update({'color': list(node.color), 'border_color': list(node.border_color), 'border_width': node.border_width})
    if isinstance(node, UILabel):
        data.update({'text': node.text, 'font_size': node.font_size, 'color': list(node.color), 'align': node.align})
    if isinstance(node, Light2D):
        data.update({'radius': node.radius, 'energy': node.energy, 'color': list(node.color), 'softness': node.softness, 'enabled': node.enabled})
    if isinstance(node, CanvasModulate):
        data.update({'color': list(node.color)})
    if isinstance(node, Navigation2D):
        data.update({'cell_size': node.cell_size, 'nav_width': node.width, 'nav_height': node.height, 'allow_diagonal': node.allow_diagonal, 'blocked': sorted(node.blocked), 'debug_visible': node.debug_visible})
    if isinstance(node, NavigationAgent2D):
        data.update({'target_position': _v2(node.target_position), 'speed': node.speed, 'enabled': node.enabled, 'arrival_distance': node.arrival_distance})
    if isinstance(node, MeshInstance3D):
        data.update({'primitive': node.primitive, 'mesh_path': node.mesh_path, 'size3d': _v3(node.size), 'color3d': list(node.color), 'wireframe': node.wireframe, 'shaded': node.shaded, 'double_sided': node.double_sided, 'segments': node.segments, 'rings': node.rings, 'cast_shadow3d': node.cast_shadow, 'receive_light3d': node.receive_light})
    if isinstance(node, Camera3DNode):
        data.update({'current3d': node.current, 'fov': node.fov, 'near': node.near, 'far': node.far, 'orthographic': node.orthographic, 'ortho_size': node.ortho_size, 'cull_mask3d': int(node.cull_mask)})
    if isinstance(node, DirectionalLight3D):
        data.update({'light_color3d': list(node.color), 'light_energy3d': node.energy, 'ambient3d': node.ambient, 'light_enabled3d': node.enabled})
    if isinstance(node, PointLight3D):
        data.update({'point_color3d': list(node.color), 'point_energy3d': node.energy, 'point_range3d': node.range, 'point_attenuation3d': node.attenuation, 'point_enabled3d': node.enabled})
    if isinstance(node, SpotLight3D):
        data.update({'spot_angle3d': node.spot_angle, 'spot_softness3d': node.edge_softness})
    if isinstance(node, RayCast3D):
        data.update({'ray_target3d': _v3(node.target_position), 'ray_enabled3d': node.enabled, 'ray_mask3d': int(node.collision_mask), 'ray_exclude_parent3d': node.exclude_parent})
    if isinstance(node, WorldEnvironment3D):
        data.update({'ambient_color3d': list(node.ambient_color), 'ambient_energy3d': node.ambient_energy, 'fog_enabled3d': node.fog_enabled, 'fog_color3d': list(node.fog_color), 'fog_near3d': node.fog_near, 'fog_far3d': node.fog_far, 'sky_enabled3d': node.sky_enabled, 'sky_top_color3d': list(node.sky_top_color), 'sky_bottom_color3d': list(node.sky_bottom_color)})
    if isinstance(node, Scene):
        data['background_color'] = list(node.background_color) if node.background_color is not None else None
    return data

def node_from_dict(data: Dict[str, Any]) -> Node:
    node_type = str(data.get('type', 'Node'))
    name = str(data.get('name', node_type))
    cls = NODE_TYPES.get(node_type, Node)
    if cls is Scene:
        bg = data.get('background_color')
        node: Node = Scene(name, tuple(bg) if bg is not None else None)
    elif cls is ColorRect2D:
        node = ColorRect2D(name, _vec(data.get('size'), (96, 64)), tuple(data.get('color', [86, 156, 214])))
    elif cls is Sprite2D:
        node = Sprite2D(name, str(data.get('texture', '')))
    elif cls is Label2D:
        node = Label2D(name, str(data.get('text', 'Label')), int(data.get('font_size', 24)), tuple(data.get('color', [240, 240, 245])))
    elif cls is Camera2DNode:
        node = Camera2DNode(name)
    elif cls is CollisionRect2D:
        node = CollisionRect2D(name, _vec(data.get('size'), (64, 64)))
    elif cls is Timer:
        node = Timer(name)
    elif cls is AudioStreamPlayer2D:
        node = AudioStreamPlayer2D(name)
    elif cls is Button2D:
        node = Button2D(name, str(data.get('text', 'Button')))
    elif cls is PhysicsBody2D:
        body_type = BodyType.__members__.get(str(data.get('body_type', 'DYNAMIC')), BodyType.DYNAMIC)
        node = PhysicsBody2D(name, body_type)
    elif cls is PhysicsBody3D:
        body_type = BodyType.__members__.get(str(data.get('body_type3d', 'DYNAMIC')), BodyType.DYNAMIC)
        node = PhysicsBody3D(name, body_type)
    elif cls is TileMap2D:
        node = TileMap2D(name)
    elif cls is ParticleSystem2D:
        node = ParticleSystem2D(name)
    elif cls is CanvasLayer:
        node = CanvasLayer(name)
    elif cls is Control:
        node = Control(name)
    elif cls is UIPanel:
        node = UIPanel(name)
    elif cls is UILabel:
        node = UILabel(name, str(data.get('text', 'Label')))
    elif cls is Light2D:
        node = Light2D(name)
    elif cls is CanvasModulate:
        node = CanvasModulate(name)
    elif cls is Navigation2D:
        node = Navigation2D(name)
    elif cls is NavigationAgent2D:
        node = NavigationAgent2D(name)
    elif cls is MeshInstance3D:
        node = MeshInstance3D(name, str(data.get('primitive', 'cube')))
    elif cls is Camera3DNode:
        node = Camera3DNode(name)
    elif cls is DirectionalLight3D:
        node = DirectionalLight3D(name)
    elif cls is PointLight3D:
        node = PointLight3D(name)
    elif cls is SpotLight3D:
        node = SpotLight3D(name)
    elif cls is Marker3D:
        node = Marker3D(name)
    elif cls is RayCast3D:
        node = RayCast3D(name)
    elif cls is WorldEnvironment3D:
        node = WorldEnvironment3D(name)
    else:
        node = cls(name)
    node.script_path = str(data.get('script', '') or '')
    node.groups = {str(x) for x in data.get('groups', []) if str(x).strip()}
    node.tag = str(data.get('tag', 'Untagged'))
    node.layer = int(data.get('layer', 0))
    node.signal_connections = [dict(x) for x in data.get('signal_connections', []) if isinstance(x, dict)]
    node.editor_locked = bool(data.get('editor_locked', False))
    if isinstance(node, Node2D):
        node.position = _vec(data.get('position'))
        node.rotation = float(data.get('rotation', 0))
        node.scale = _vec(data.get('scale'), (1, 1))
        node.visible = bool(data.get('visible', True))
        node.z_index = int(data.get('z_index', 0))
        node.material_path = str(data.get('material', '') or '')
    if isinstance(node, Node3D):
        node.position = _vec3(data.get('position3d', data.get('position')), (0, 0, 0))
        node.rotation = _vec3(data.get('rotation3d'), (0, 0, 0))
        node.scale = _vec3(data.get('scale3d'), (1, 1, 1))
        node.visible = bool(data.get('visible3d', data.get('visible', True)))
        node.render_layer = int(data.get('render_layer', 0))
        node.material_path = str(data.get('material3d', '') or '')
    if isinstance(node, Sprite2D):
        node.centered = bool(data.get('centered', True))
        node.flip_h = bool(data.get('flip_h', False))
        node.flip_v = bool(data.get('flip_v', False))
        node.opacity = float(data.get('opacity', 1))
    if isinstance(node, Label2D):
        node.font_path = str(data.get('font_path', ''))
    if isinstance(node, Camera2DNode):
        node.current = bool(data.get('current', True))
        node.zoom = float(data.get('camera_zoom', 1))
    if isinstance(node, CollisionRect2D):
        node.is_trigger = bool(data.get('is_trigger', False))
        node.debug_visible = bool(data.get('debug_visible', False))
    if isinstance(node, PhysicsBody2D):
        node.velocity = _vec(data.get('velocity'))
        node.mass = float(data.get('mass', 1))
        node.gravity_scale = float(data.get('gravity_scale', 1))
        node.restitution = float(data.get('restitution', 0))
        node.friction = float(data.get('friction', 0.2))
        node.collider.size = _vec(data.get('collider_size'), (32, 32))
        node.collider.offset = _vec(data.get('collider_offset'))
        node.collider.enabled = bool(data.get('collider_enabled', True))
        node.collider.is_trigger = bool(data.get('collider_trigger', False))
        node.collision_layer = int(data.get('collision_layer', 1))
        node.collision_mask = int(data.get('collision_mask', 4294967295))
    if isinstance(node, PhysicsBody3D):
        node.velocity = _vec3(data.get('velocity3d'))
        node.mass = float(data.get('mass3d', 1))
        node.gravity_scale = float(data.get('gravity_scale3d', 1))
        node.restitution = float(data.get('restitution3d', 0))
        node.friction = float(data.get('friction3d', 0.2))
        node.collider.size = _vec3(data.get('collider_size3d'), (1, 1, 1))
        node.collider.offset = _vec3(data.get('collider_offset3d'))
        node.collider.enabled = bool(data.get('collider_enabled3d', True))
        node.collider.is_trigger = bool(data.get('collider_trigger3d', False))
        node.collision_layer = int(data.get('collision_layer3d', 1))
        node.collision_mask = int(data.get('collision_mask3d', 4294967295))
    if isinstance(node, Timer):
        node.wait_time = float(data.get('wait_time', 1))
        node.one_shot = bool(data.get('one_shot', False))
        node.autostart = bool(data.get('autostart', False))
        node.paused = bool(data.get('paused', False))
    if isinstance(node, AudioStreamPlayer2D):
        node.stream_path = str(data.get('stream', ''))
        node.autoplay = bool(data.get('autoplay', False))
        node.loop = bool(data.get('loop', False))
        node.volume = float(data.get('volume', 1))
    if isinstance(node, Button2D):
        node.size = _vec(data.get('size'), (160, 44))
        node.color = tuple(data.get('color', [55, 65, 82]))
        node.hover_color = tuple(data.get('hover_color', [72, 90, 116]))
        node.text_color = tuple(data.get('text_color', [245, 245, 248]))
        node.disabled = bool(data.get('disabled', False))
        node.screen_space = bool(data.get('screen_space', True))
    if isinstance(node, TileMap2D):
        node.texture_path = str(data.get('texture', ''))
        node.tile_size = _vec(data.get('tile_size'), (32, 32))
        node.atlas_columns = max(1, int(data.get('atlas_columns', 8)))
        node.margin = int(data.get('margin', 0))
        node.spacing = int(data.get('spacing', 0))
        node.tiles = {str(k): int(v) for k, v in dict(data.get('tiles', {})).items()}
        node.collision_tiles = {int(x) for x in data.get('collision_tiles', [])}
        node.debug_grid = bool(data.get('debug_grid', False))
    if isinstance(node, ParticleSystem2D):
        node.emitting = bool(data.get('emitting', True))
        node.amount = int(data.get('amount', 128))
        node.emission_rate = float(data.get('emission_rate', 40))
        node.lifetime = float(data.get('lifetime', 1.5))
        node.speed_min = float(data.get('speed_min', 40))
        node.speed_max = float(data.get('speed_max', 140))
        node.direction = float(data.get('direction', -90))
        node.spread = float(data.get('spread', 45))
        node.gravity = _vec(data.get('gravity'), (0, 90))
        node.color_start = tuple(data.get('color_start', [255, 210, 100, 255]))
        node.color_end = tuple(data.get('color_end', [255, 80, 60, 0]))
        node.size_start = float(data.get('size_start', 5))
        node.size_end = float(data.get('size_end', 1))
        node.texture_path = str(data.get('texture', ''))
        node.local_coords = bool(data.get('local_coords', True))
    if isinstance(node, CanvasLayer):
        node.layer = int(data.get('canvas_layer', 0))
        node.visible = bool(data.get('canvas_visible', True))
    if isinstance(node, Control):
        node.size = _vec(data.get('size'), (160, 64))
        a = list(data.get('anchors', [0, 0, 0, 0]))
        o = list(data.get('offsets', [0, 0, 160, 64]))
        a = (a + [0, 0, 0, 0])[:4]
        o = (o + [0, 0, 160, 64])[:4]
        node.anchor_left, node.anchor_top, node.anchor_right, node.anchor_bottom = map(float, a)
        node.offset_left, node.offset_top, node.offset_right, node.offset_bottom = map(float, o)
        node.mouse_filter = str(data.get('mouse_filter', 'stop'))
    if isinstance(node, UIPanel):
        node.color = tuple(data.get('color', [40, 44, 54, 230]))
        node.border_color = tuple(data.get('border_color', [74, 82, 100, 255]))
        node.border_width = int(data.get('border_width', 0))
    if isinstance(node, UILabel):
        node.text = str(data.get('text', 'Label'))
        node.font_size = int(data.get('font_size', 20))
        node.color = tuple(data.get('color', [245, 245, 248, 255]))
        node.align = str(data.get('align', 'left'))
    if isinstance(node, Light2D):
        node.radius = float(data.get('radius', 180))
        node.energy = float(data.get('energy', 1))
        node.color = tuple(data.get('color', [255, 225, 170]))
        node.softness = float(data.get('softness', 0.7))
        node.enabled = bool(data.get('enabled', True))
    if isinstance(node, CanvasModulate):
        node.color = tuple(data.get('color', [255, 255, 255, 255]))
    if isinstance(node, Navigation2D):
        node.cell_size = float(data.get('cell_size', 32))
        node.width = int(data.get('nav_width', 40))
        node.height = int(data.get('nav_height', 24))
        node.allow_diagonal = bool(data.get('allow_diagonal', False))
        node.blocked = {str(x) for x in data.get('blocked', [])}
        node.debug_visible = bool(data.get('debug_visible', False))
    if isinstance(node, NavigationAgent2D):
        node.target_position = _vec(data.get('target_position'))
        node.speed = float(data.get('speed', 120))
        node.enabled = bool(data.get('enabled', True))
        node.arrival_distance = float(data.get('arrival_distance', 4))
    if isinstance(node, MeshInstance3D):
        node.primitive = str(data.get('primitive', 'cube'))
        node.mesh_path = str(data.get('mesh_path', '') or '')
        node.size = _vec3(data.get('size3d'), (1, 1, 1))
        node.color = tuple(data.get('color3d', [110, 170, 235]))
        node.wireframe = bool(data.get('wireframe', False))
        node.shaded = bool(data.get('shaded', True))
        node.double_sided = bool(data.get('double_sided', True))
        node.segments = max(6, int(data.get('segments', 14)))
        node.rings = max(4, int(data.get('rings', 9)))
        node.cast_shadow = bool(data.get('cast_shadow3d', True))
        node.receive_light = bool(data.get('receive_light3d', True))
    if isinstance(node, Camera3DNode):
        node.current = bool(data.get('current3d', True))
        node.fov = float(data.get('fov', 70))
        node.near = float(data.get('near', 0.05))
        node.far = float(data.get('far', 2000))
        node.orthographic = bool(data.get('orthographic', False))
        node.ortho_size = float(data.get('ortho_size', 10))
        node.cull_mask = int(data.get('cull_mask3d', 4294967295))
    if isinstance(node, DirectionalLight3D):
        node.color = tuple(data.get('light_color3d', [255, 244, 220]))
        node.energy = float(data.get('light_energy3d', 1))
        node.ambient = float(data.get('ambient3d', 0.22))
        node.enabled = bool(data.get('light_enabled3d', True))
    if isinstance(node, PointLight3D):
        node.color = tuple(data.get('point_color3d', [255, 220, 170]))
        node.energy = float(data.get('point_energy3d', 1))
        node.range = float(data.get('point_range3d', 8))
        node.attenuation = float(data.get('point_attenuation3d', 2))
        node.enabled = bool(data.get('point_enabled3d', True))
    if isinstance(node, SpotLight3D):
        node.spot_angle = float(data.get('spot_angle3d', 45))
        node.edge_softness = float(data.get('spot_softness3d', 0.2))
    if isinstance(node, RayCast3D):
        node.target_position = _vec3(data.get('ray_target3d'), (0, 0, -5))
        node.enabled = bool(data.get('ray_enabled3d', True))
        node.collision_mask = int(data.get('ray_mask3d', 4294967295))
        node.exclude_parent = bool(data.get('ray_exclude_parent3d', True))
    if isinstance(node, WorldEnvironment3D):
        node.ambient_color = tuple(data.get('ambient_color3d', [255, 255, 255]))
        node.ambient_energy = float(data.get('ambient_energy3d', 0.22))
        node.fog_enabled = bool(data.get('fog_enabled3d', False))
        node.fog_color = tuple(data.get('fog_color3d', [100, 120, 145]))
        node.fog_near = float(data.get('fog_near3d', 20))
        node.fog_far = float(data.get('fog_far3d', 100))
        node.sky_enabled = bool(data.get('sky_enabled3d', False))
        node.sky_top_color = tuple(data.get('sky_top_color3d', [35, 50, 82]))
        node.sky_bottom_color = tuple(data.get('sky_bottom_color3d', [145, 185, 225]))
    for child_data in data.get('children', []):
        node.add_child(node_from_dict(child_data))
    return node

def _node_diff(base: dict[str, Any], derived: dict[str, Any]) -> dict[str, Any]:
    diff: dict[str, Any] = {'props': {}, 'children_changed': {}, 'children_added': [], 'children_removed': []}
    for key, value in derived.items():
        if key == 'children':
            continue
        if base.get(key) != value:
            diff['props'][key] = copy.deepcopy(value)
    bchildren = {str(c.get('name')): c for c in base.get('children', []) if isinstance(c, dict)}
    dchildren = {str(c.get('name')): c for c in derived.get('children', []) if isinstance(c, dict)}
    for name in bchildren.keys() - dchildren.keys():
        diff['children_removed'].append(name)
    for name in dchildren.keys() - bchildren.keys():
        diff['children_added'].append(copy.deepcopy(dchildren[name]))
    for name in bchildren.keys() & dchildren.keys():
        if bchildren[name].get('type') != dchildren[name].get('type'):
            diff['children_removed'].append(name)
            diff['children_added'].append(copy.deepcopy(dchildren[name]))
            continue
        child_diff = _node_diff(bchildren[name], dchildren[name])
        if _diff_nonempty(child_diff):
            diff['children_changed'][name] = child_diff
    b_order = [c.get('name') for c in base.get('children', [])]
    d_order = [c.get('name') for c in derived.get('children', [])]
    if b_order != d_order:
        diff['children_order'] = d_order
    return diff

def _diff_nonempty(diff: dict[str, Any]) -> bool:
    return bool(diff.get('props') or diff.get('children_changed') or diff.get('children_added') or diff.get('children_removed') or diff.get('children_order'))

def _apply_node_diff(base: dict[str, Any], diff: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(base)
    result.update(copy.deepcopy(diff.get('props', {})))
    children = [c for c in result.get('children', []) if c.get('name') not in set(diff.get('children_removed', []))]
    by_name = {str(c.get('name')): c for c in children}
    for name, child_diff in dict(diff.get('children_changed', {})).items():
        if name in by_name:
            updated = _apply_node_diff(by_name[name], child_diff)
            idx = children.index(by_name[name])
            children[idx] = updated
            by_name[name] = updated
    for child in diff.get('children_added', []):
        children.append(copy.deepcopy(child))
    order = diff.get('children_order')
    if order:
        rank = {str(name): i for i, name in enumerate(order)}
        children.sort(key=lambda c: rank.get(str(c.get('name')), len(rank)))
    result['children'] = children
    return result

def save_scene(scene: Scene, path: str | Path) -> Path:
    path = Path(path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    current = node_to_dict(scene)
    inherited = str(getattr(scene, 'inherited_from', '') or '')
    if inherited:
        base_path = Path(inherited)
        if not base_path.is_absolute():
            base_path = (path.parent / base_path).resolve()
        if base_path.exists() and base_path != path:
            base_scene = load_scene(base_path)
            base_dict = node_to_dict(base_scene)
            override = _node_diff(base_dict, current)
            rel = os.path.relpath(base_path, path.parent).replace('\\', '/')
            payload = {'format': 'vworks_scene', 'version': SCENE_VERSION, 'inheritance': {'base': rel}, 'overrides': override}
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
            scene.inherited_from = rel
            return path
    payload = {'format': 'vworks_scene', 'version': SCENE_VERSION, 'scene': current}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    return path

def load_scene(path: str | Path, _stack: set[Path] | None=None) -> Scene:
    path = Path(path).resolve()
    stack = set() if _stack is None else _stack
    if path in stack:
        raise ValueError(f'Scene inheritance cycle detected at {path}')
    stack.add(path)
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
        if payload.get('format') != 'vworks_scene':
            raise ValueError('Not a V Works .vscene file')
        inheritance = payload.get('inheritance')
        if inheritance and inheritance.get('base'):
            ref = str(inheritance['base'])
            base_path = Path(ref)
            base_path = base_path.resolve() if base_path.is_absolute() else (path.parent / base_path).resolve()
            base_scene = load_scene(base_path, stack)
            merged = _apply_node_diff(node_to_dict(base_scene), dict(payload.get('overrides', {})))
            root = node_from_dict(merged)
            if not isinstance(root, Scene):
                scene = Scene(root.name)
                [scene.add_child(c) for c in root.get_children()]
                root = scene
            root.inherited_from = ref
            return root
        root = node_from_dict(payload['scene'])
        if isinstance(root, Scene):
            return root
        scene = Scene(root.name)
        for child in root.get_children():
            root.remove_child(child)
            scene.add_child(child)
        return scene
    finally:
        stack.discard(path)

def create_inherited_scene(base_path: str | Path, destination: str | Path) -> Path:
    base_path = Path(base_path).resolve()
    destination = Path(destination).resolve()
    scene = load_scene(base_path)
    scene.inherited_from = os.path.relpath(base_path, destination.parent).replace('\\', '/')
    return save_scene(scene, destination)

def save_prefab(node: Node, path: str | Path) -> Path:
    path = Path(path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {'format': 'vworks_prefab', 'version': 2, 'node': node_to_dict(node)}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    return path

def load_prefab(path: str | Path) -> Node:
    path = Path(path).resolve()
    payload = json.loads(path.read_text(encoding='utf-8'))
    if payload.get('format') != 'vworks_prefab':
        raise ValueError('Not a V Works .vprefab file')
    return node_from_dict(payload['node'])
