from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..scene import Camera2DNode, CanvasLayer, ColorRect2D, Label2D, Light2D, MeshInstance3D, Camera3DNode, DirectionalLight3D, PointLight3D, SpotLight3D, WorldEnvironment3D, Marker3D, RayCast3D, ParticleSystem2D, TileMap2D, Navigation2D, NavigationAgent2D, UIPanel, UILabel, Timer, Button2D
from ..physics import RigidBody2D, StaticBody2D, StaticBody3D, RigidBody3D, CharacterBody3D, Area2D
from ..utils.vmath import Vector2, Vector3


@dataclass(frozen=True)
class TemplateSpec:
    id: str
    title: str
    category: str
    description: str
    features: tuple[str, ...]


TEMPLATES = (
    TemplateSpec('empty', 'Empty 2D', 'Basics', 'A clean scene with no additional nodes.', ('Scene', 'Node')),
    TemplateSpec('2d_starter', '2D Starter', 'Basics', 'Text, colored shapes, and a light.', ('Label2D', 'ColorRect2D', 'Light2D')),
    TemplateSpec('3d_starter', '3D Starter', '3D', 'A 3D room with camera, lights, physics and primitives.', ('Camera3D', 'MeshInstance3D', 'RigidBody3D')),
    TemplateSpec('platformer', '2D Platformer', '2D Games', 'Basic side-view character, ground, jump and movement script.', ('CharacterBody2D', 'Physics', 'Input')),
    TemplateSpec('top_down', 'Top Down 2D', '2D Games', 'A keyboard-controlled top-down character.', ('Camera2D', 'CharacterBody2D', 'Input')),
    TemplateSpec('ui_app', 'UI Application', 'UI', 'Responsive canvas and label with anchor settings.', ('CanvasLayer', 'UIPanel', 'UILabel')),
    TemplateSpec('tilemap', 'TileMap World', '2D Games', 'A grid map with tiles and a debug grid.', ('TileMap2D', 'Grid', 'Tiles')),
    TemplateSpec('physics_2d', 'Physics Sandbox', '2D Labs', 'Falling colored blocks and a static floor to study collision.', ('RigidBody2D', 'StaticBody2D', 'Colliders')),
    TemplateSpec('particles_2d', 'Particle Playground', '2D Labs', 'Two emitters with contrasting settings and a visual guide.', ('ParticleSystem2D', 'Light2D', 'Parameters')),
    TemplateSpec('lights_2d', '2D Lighting Studio', '2D Labs', 'A small scene containing lights and colored surfaces.', ('Light2D', 'ColorRect2D', 'Layers')),
    TemplateSpec('signals_2d', 'Signals & Timers', '2D Labs', 'Scene with a button, timer and area nodes to inspect signals.', ('Button2D', 'Timer', 'Area2D')),
    TemplateSpec('navigation_2d', 'Navigation Lab', '2D Labs', 'Navigation map and an agent for pathfinding experiments.', ('Navigation2D', 'NavigationAgent2D', 'Routes')),
    TemplateSpec('ui_dashboard', 'UI Dashboard', 'UI', 'A multi-panel dashboard with text, anchors and canvas.', ('CanvasLayer', 'UIPanel', 'UILabel')),
    TemplateSpec('arena_3d', '3D Arena Starter', '3D Games', 'Blockout arena, spawn markers, a camera and world lighting.', ('MeshInstance3D', 'Marker3D', 'Lighting')),
    TemplateSpec('third_person_3d', 'Third Person 3D', '3D Games', 'Character, follow-camera starting rig and ground; movement is an exercise.', ('CharacterBody3D', 'Camera3D', 'Scene hierarchy')),
    TemplateSpec('obstacles_3d', '3D Obstacle Course', '3D Games', 'A low-poly level featuring platforms, blocks and ramps.', ('MeshInstance3D', 'StaticBody3D', 'Levels')),
    TemplateSpec('physics_3d', '3D Physics Lab', '3D Labs', 'Dynamic cubes and spheres above a collision floor.', ('RigidBody3D', 'Collider3D', 'Gravity')),
    TemplateSpec('lighting_3d', '3D Lighting Studio', '3D Labs', 'Environment, directional, point and spot lights.', ('WorldEnvironment3D', 'PointLight3D', 'SpotLight3D')),
    TemplateSpec('raycast_3d', 'RayCast 3D Lab', '3D Labs', 'Camera and raycaster with simple targets for collision inspection.', ('RayCast3D', 'Marker3D', 'Physics')),
)


def get_template(template_id: str) -> TemplateSpec:
    return next((item for item in TEMPLATES if item.id == template_id), TEMPLATES[0])


def _mesh(parent, name: str, pos, size, color, primitive='cube'):
    mesh = MeshInstance3D(name, primitive)
    mesh.position = Vector3(*pos)
    mesh.size = Vector3(*size)
    mesh.color = color
    parent.add_child(mesh)
    return mesh


def _solid(parent, name: str, pos, size, color):
    body = StaticBody3D(name)
    body.position = Vector3(*pos)
    body.collider.size = Vector3(*size)
    _mesh(body, 'Visual', (0, 0, 0), size, color)
    parent.add_child(body)
    return body


def _base_3d(scene, camera_pos=(0, 4, 11)):
    environment = WorldEnvironment3D('Environment')
    environment.ambient_energy = 0.32
    environment.sky_enabled = True
    scene.add_child(environment)
    sun = DirectionalLight3D('Sun')
    sun.rotation = Vector3(-0.65, -0.45, 0)
    scene.add_child(sun)
    camera = Camera3DNode('Camera3D')
    camera.position = Vector3(*camera_pos)
    camera.rotation = Vector3(-0.28, 0, 0)
    scene.add_child(camera)
    return camera


def populate_extended_template(template_id: str, scene, root: Path) -> bool:
    if template_id == 'physics_2d':
        scene.add_child(Label2D('Hint', 'RigidBody2D + StaticBody2D | Run to simulate', 22))
        floor = StaticBody2D('Floor')
        floor.position = Vector2(140, 565)
        floor.collider.size = Vector2(860, 42)
        floor.add_child(ColorRect2D('Visual', Vector2(860, 42), (77, 92, 122)))
        scene.add_child(floor)
        for i, color in enumerate(((77, 166, 238), (226, 153, 85), (144, 204, 123))):
            body = RigidBody2D(f'FallingBlock{i + 1}')
            body.position = Vector2(260 + i * 165, 130 + i * 35)
            body.collider.size = Vector2(65, 65)
            body.add_child(ColorRect2D('Visual', Vector2(65, 65), color))
            scene.add_child(body)
    elif template_id == 'particles_2d':
        scene.add_child(Label2D('Hint', 'Select each ParticleSystem2D to tune emission', 22))
        for i, color in enumerate(((255, 206, 99, 255), (95, 185, 255, 255))):
            emitter = ParticleSystem2D(f'Emitter{i + 1}')
            emitter.position = Vector2(340 + i * 350, 380)
            emitter.color_start = color
            emitter.emission_rate = 32.0 + 25.0 * i
            emitter.spread = 48 + 30 * i
            scene.add_child(emitter)
        light = Light2D('BackgroundLight')
        light.position = Vector2(520, 360)
        scene.add_child(light)
    elif template_id == 'lights_2d':
        scene.add_child(Label2D('Hint', 'Lighting studio | Inspect energy, radius and colors', 22))
        for i in range(4):
            surface = ColorRect2D(f'ColorSurface{i + 1}', Vector2(135, 135), (75 + i * 26, 85 + i * 20, 120 + i * 13))
            surface.position = Vector2(165 + i * 185, 320)
            scene.add_child(surface)
            light = Light2D(f'Spot{i + 1}')
            light.position = Vector2(230 + i * 185, 340)
            scene.add_child(light)
    elif template_id == 'signals_2d':
        hint = Label2D('Hint', 'Select Button / Timer / Trigger, then open Signals', 22)
        hint.position = Vector2(55, 40)
        scene.add_child(hint)
        button = Button2D('TestButton')
        button.position = Vector2(160, 170)
        scene.add_child(button)
        timer = Timer('RepeatingTimer')
        scene.add_child(timer)
        trigger = Area2D('TriggerArea')
        trigger.position = Vector2(465, 260)
        trigger.collider.size = Vector2(180, 110)
        scene.add_child(trigger)
    elif template_id == 'navigation_2d':
        scene.add_child(Label2D('Hint', 'Navigation2D | Configure walkable region and the agent', 22))
        navigation = Navigation2D('Navigation2D')
        scene.add_child(navigation)
        agent = NavigationAgent2D('NavigationAgent2D')
        agent.position = Vector2(160, 210)
        scene.add_child(agent)
        for i in range(3):
            wall = ColorRect2D(f'Obstacle{i + 1}', Vector2(110, 64), (85, 100, 120))
            wall.position = Vector2(340 + i * 140, 240 + (i % 2) * 120)
            scene.add_child(wall)
    elif template_id == 'ui_dashboard':
        canvas = CanvasLayer('Dashboard')
        scene.add_child(canvas)
        background = UIPanel('Background')
        background.set_anchor_preset('full_rect')
        canvas.add_child(background)
        for i, title in enumerate(('Health', 'Inventory', 'Objectives')):
            panel = UIPanel(f'{title}Panel')
            panel.anchor_left = i / 3
            panel.anchor_right = (i + 1) / 3
            panel.offset_left = 16
            panel.offset_right = -16
            panel.offset_top = 80
            panel.offset_bottom = 320
            background.add_child(panel)
            text = UILabel(f'{title}Label', title)
            text.font_size = 25
            text.offset_left = 16
            text.offset_top = 20
            panel.add_child(text)
    elif template_id == 'arena_3d':
        _base_3d(scene, (0, 7, 16))
        _solid(scene, 'ArenaFloor', (0, -0.35, 0), (24, 0.7, 24), (65, 75, 92))
        for i, pos, size in (
            (1, (0, 1.6, -11.5), (24, 3.2, 1)),
            (2, (0, 1.6, 11.5), (24, 3.2, 1)),
            (3, (-11.5, 1.6, 0), (1, 3.2, 24)),
            (4, (11.5, 1.6, 0), (1, 3.2, 24)),
        ):
            _solid(scene, f'Wall{i}', pos, size, (91, 107, 129))
        for i, pos in enumerate(((-7, 0.8, -5), (7, 0.8, -4), (-6, 0.8, 7), (6, 0.8, 6))):
            _solid(scene, f'Cover{i + 1}', pos, (2, 1.6, 2), (72, 126, 155))
        for i, pos in enumerate(((0, 1, 8), (-8, 1, -8), (8, 1, -8))):
            spawn = Marker3D(f'Spawn{i + 1}')
            spawn.position = Vector3(*pos)
            scene.add_child(spawn)
    elif template_id == 'third_person_3d':
        camera = _base_3d(scene, (0, 3.7, 7))
        scene.remove_child(camera)
        _solid(scene, 'Ground', (0, -0.25, 0), (18, 0.5, 18), (79, 89, 106))
        player = CharacterBody3D('Player')
        player.position = Vector3(0, 1.4, 0)
        player.tag = 'Player'
        _mesh(player, 'CapsulePlaceholder', (0, 0, 0), (0.85, 1.6, 0.85), (87, 169, 232), 'sphere')
        player.add_child(camera)
        scene.add_child(player)
        for i in range(4):
            _solid(scene, f'Landmark{i + 1}', (-6 + i * 4, 0.7, -4), (1.5, 1.4, 1.5), (183, 134, 90))
    elif template_id == 'obstacles_3d':
        _base_3d(scene, (0, 7, 15))
        _solid(scene, 'StartingGround', (0, -0.2, 4), (10, 0.4, 8), (73, 85, 102))
        for i in range(7):
            _solid(scene, f'Platform{i + 1}', (2.8 * ((i % 3) - 1), 0.35 + i * 0.3, 0 - i * 3), (3, 0.6, 2.5), (65 + i * 17, 135, 182))
        start = Marker3D('Start')
        start.position = Vector3(0, 1, 6)
        scene.add_child(start)
    elif template_id == 'physics_3d':
        _base_3d(scene)
        _solid(scene, 'Floor', (0, -0.25, 0), (14, 0.5, 14), (75, 83, 101))
        for i in range(6):
            body = RigidBody3D(f'DynamicBody{i + 1}')
            body.position = Vector3((i % 3 - 1) * 2, 2.5 + i, i // 3 * 2 - 1)
            body.collider.size = Vector3(1, 1, 1)
            _mesh(body, 'Visual', (0, 0, 0), (1, 1, 1), (80 + i * 21, 130, 210 - i * 12), 'sphere' if i % 2 else 'cube')
            scene.add_child(body)
    elif template_id == 'lighting_3d':
        _base_3d(scene)
        _solid(scene, 'Floor', (0, -0.25, 0), (14, 0.5, 14), (74, 83, 100))
        for i in range(5):
            _mesh(scene, f'Statue{i + 1}', (i * 2 - 4, 1.3, 0), (1.5, 2.6, 1.5), (170, 155, 124), 'sphere' if i % 2 else 'cube')
        for i, pos, color in ((1, (-3, 3, 2), (255, 150, 110)), (2, (3, 3, 2), (95, 160, 255))):
            light = PointLight3D(f'PointLight{i}')
            light.position = Vector3(*pos)
            light.color = color
            light.range = 10
            scene.add_child(light)
        spot = SpotLight3D('SpotLight3D')
        spot.position = Vector3(0, 5, -3)
        scene.add_child(spot)
    elif template_id == 'raycast_3d':
        _base_3d(scene)
        _solid(scene, 'Floor', (0, -0.25, 0), (12, 0.5, 12), (64, 79, 99))
        for i in range(3):
            _solid(scene, f'Target{i + 1}', (i * 2.5 - 2.5, 1, -1), (1.5, 2, 1.5), (195, 95 + i * 42, 115))
        ray = RayCast3D('DetectionRay')
        ray.position = Vector3(0, 2, 4)
        ray.target_position = Vector3(0, 0, -8)
        scene.add_child(ray)
        marker = Marker3D('RayOrigin')
        marker.position = ray.position
        scene.add_child(marker)
    else:
        return False
    return True


def write_template_guide(template_id: str, project_root: Path) -> None:
    spec = get_template(template_id)
    lines = [f'# {spec.title}', '', spec.description, '', '## What to inspect', '']
    lines.extend(f'- {feature}' for feature in spec.features)
    lines.extend(['', '## Try it', '', '1. Open `scenes/main.vscene` in the editor.', '2. Explore the Scene dock, select a node and inspect its properties.', '3. Use the 2D or 3D workspace depending on the project.', '4. Start the Game View or run the project to examine runtime behavior.', '5. Change a parameter, save, and compare the result.', '', 'A starter scene illustrates engine features; gameplay systems not explicitly scripted in the scene are exercises for you to implement.', ''])
    (project_root / 'TEMPLATE_GUIDE.md').write_text('\n'.join(lines), encoding='utf-8')
