from __future__ import annotations
import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable
from ..scene import Camera2DNode, CanvasLayer, ColorRect2D, Label2D, Light2D, Node2D, ParticleSystem2D, Scene, TileMap2D, UILabel, UIPanel, MeshInstance3D, Camera3DNode, DirectionalLight3D, PointLight3D, SpotLight3D, WorldEnvironment3D, Marker3D, RayCast3D
from ..physics import CharacterBody2D, StaticBody2D, StaticBody3D, RigidBody3D
from ..scene.serialization import save_scene
from ..utils.vmath import Vector2, Vector3
PROJECT_FILE = 'project.vproject'
PROJECT_FORMAT_VERSION = 3

@dataclass
class BuildScene:
    path: str
    enabled: bool = True

    @classmethod
    def from_value(cls, value: Any) -> 'BuildScene':
        if isinstance(value, str):
            return cls(value, True)
        if isinstance(value, dict):
            return cls(str(value.get('path', '')), bool(value.get('enabled', True)))
        return cls(str(value), True)

    def to_dict(self) -> Dict[str, Any]:
        return {'path': self.path, 'enabled': self.enabled}

@dataclass
class ProjectWindowConfig:
    width: int = 1280
    height: int = 720
    fullscreen: bool = False
    borderless: bool = False
    resizable: bool = True
    vsync: bool = True

@dataclass
class ProjectRuntimeConfig:
    target_fps: int = 120
    physics_fps: int = 60
    gravity: float = 980.0
    gravity_3d: float = -9.81
    debug_overlay: bool = False
    debug_collisions: bool = False
    profiler_overlay: bool = False
    background_color: tuple[int, int, int] = (22, 24, 31)

@dataclass
class ProjectBuildConfig:
    product_name: str = 'V Works Game'
    version: str = '0.1.0'
    company: str = 'VVittox'
    onefile: bool = False
    debug_console: bool = False
    clean_build: bool = True
    scenes: list[BuildScene] = field(default_factory=list)

@dataclass
class ProjectEditorConfig:
    autosave_enabled: bool = True
    autosave_seconds: int = 60
    recovery_keep: int = 10
    grid_size: int = 16
    show_collision_shapes: bool = True
DEFAULT_INPUT_MAP: dict[str, list[str]] = {'ui_left': ['left', 'a'], 'ui_right': ['right', 'd'], 'ui_up': ['up', 'w'], 'ui_down': ['down', 's'], 'ui_accept': ['return', 'space'], 'ui_cancel': ['escape']}

@dataclass
class ProjectConfig:
    root: Path
    name: str
    main_scene: str = 'scenes/main.vscene'
    icon: str = 'icon.png'
    window: ProjectWindowConfig = field(default_factory=ProjectWindowConfig)
    runtime: ProjectRuntimeConfig = field(default_factory=ProjectRuntimeConfig)
    build: ProjectBuildConfig = field(default_factory=ProjectBuildConfig)
    editor: ProjectEditorConfig = field(default_factory=ProjectEditorConfig)
    input_map: dict[str, list[str]] = field(default_factory=lambda: {k: list(v) for k, v in DEFAULT_INPUT_MAP.items()})
    tags: list[str] = field(default_factory=lambda: ['Untagged', 'Player', 'Enemy', 'Collectible', 'UI'])
    layers: list[str] = field(default_factory=lambda: ['Default'] + [f'Layer {i}' for i in range(1, 32)])
    enabled_plugins: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.root = Path(self.root).resolve()
        self.ensure_build_scenes()

    @property
    def path(self) -> Path:
        return self.root / PROJECT_FILE

    @property
    def main_scene_path(self) -> Path:
        return (self.root / self.main_scene).resolve()

    @property
    def icon_path(self) -> Path:
        return (self.root / self.icon).resolve()

    @property
    def enabled_build_scenes(self) -> list[BuildScene]:
        return [s for s in self.build.scenes if s.enabled and s.path]

    def scene_path(self, scene: str | int) -> Path:
        if isinstance(scene, int):
            enabled = self.enabled_build_scenes
            if scene < 0 or scene >= len(enabled):
                raise IndexError(f'Build scene index out of range: {scene}')
            scene = enabled[scene].path
        return (self.root / str(scene)).resolve()

    def ensure_build_scenes(self) -> None:
        normalized: list[BuildScene] = []
        seen: set[str] = set()
        for raw in self.build.scenes:
            scene = raw if isinstance(raw, BuildScene) else BuildScene.from_value(raw)
            path = scene.path.replace('\\', '/').strip()
            if not path or path in seen:
                continue
            normalized.append(BuildScene(path, scene.enabled))
            seen.add(path)
        if self.main_scene and self.main_scene not in seen:
            normalized.insert(0, BuildScene(self.main_scene, True))
        self.build.scenes = normalized

    def add_build_scene(self, path: str | Path, enabled: bool=True) -> BuildScene:
        p = Path(path)
        if p.is_absolute():
            try:
                rel = p.resolve().relative_to(self.root)
                text = rel.as_posix()
            except ValueError as exc:
                raise ValueError('Build scenes must be inside the project folder') from exc
        else:
            text = p.as_posix()
        existing = next((s for s in self.build.scenes if s.path == text), None)
        if existing:
            existing.enabled = enabled
            return existing
        scene = BuildScene(text, enabled)
        self.build.scenes.append(scene)
        return scene

    def set_main_scene(self, path: str | Path) -> None:
        p = Path(path)
        if p.is_absolute():
            p = p.resolve().relative_to(self.root)
        self.main_scene = p.as_posix()
        self.add_build_scene(self.main_scene, True)

    def to_dict(self) -> Dict[str, Any]:
        self.ensure_build_scenes()
        return {'format': 'vworks_project', 'version': PROJECT_FORMAT_VERSION, 'name': self.name, 'main_scene': self.main_scene, 'icon': self.icon, 'window': {'width': self.window.width, 'height': self.window.height, 'fullscreen': self.window.fullscreen, 'borderless': self.window.borderless, 'resizable': self.window.resizable, 'vsync': self.window.vsync}, 'runtime': {'target_fps': self.runtime.target_fps, 'physics_fps': self.runtime.physics_fps, 'gravity': self.runtime.gravity, 'gravity_3d': self.runtime.gravity_3d, 'debug_overlay': self.runtime.debug_overlay, 'debug_collisions': self.runtime.debug_collisions, 'profiler_overlay': self.runtime.profiler_overlay, 'background_color': list(self.runtime.background_color)}, 'input_map': self.input_map, 'tags': list(dict.fromkeys(self.tags)), 'layers': (list(self.layers) + [f'Layer {i}' for i in range(32)])[:32], 'enabled_plugins': list(dict.fromkeys(self.enabled_plugins)), 'editor': {'autosave_enabled': self.editor.autosave_enabled, 'autosave_seconds': self.editor.autosave_seconds, 'recovery_keep': self.editor.recovery_keep, 'grid_size': self.editor.grid_size, 'show_collision_shapes': self.editor.show_collision_shapes}, 'build': {'product_name': self.build.product_name, 'version': self.build.version, 'company': self.build.company, 'onefile': self.build.onefile, 'debug_console': self.build.debug_console, 'clean_build': self.build.clean_build, 'scenes': [s.to_dict() for s in self.build.scenes]}}

    def save(self) -> Path:
        self.root.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding='utf-8')
        return self.path

    @classmethod
    def load(cls, root_or_file: str | Path) -> 'ProjectConfig':
        p = Path(root_or_file).resolve()
        path = p if p.is_file() else p / PROJECT_FILE
        payload = json.loads(path.read_text(encoding='utf-8'))
        if payload.get('format') != 'vworks_project':
            raise ValueError('Not a V Works project')
        root = path.parent
        w = payload.get('window', {})
        r = payload.get('runtime', {})
        b = payload.get('build', {})
        e = payload.get('editor', {})
        bg = r.get('background_color', [22, 24, 31])
        scenes = [BuildScene.from_value(v) for v in b.get('scenes', [])]
        input_map = payload.get('input_map') or DEFAULT_INPUT_MAP
        cfg = cls(root=root, name=str(payload.get('name') or root.name), main_scene=str(payload.get('main_scene', 'scenes/main.vscene')), icon=str(payload.get('icon', 'icon.png')), window=ProjectWindowConfig(width=int(w.get('width', 1280)), height=int(w.get('height', 720)), fullscreen=bool(w.get('fullscreen', False)), borderless=bool(w.get('borderless', False)), resizable=bool(w.get('resizable', True)), vsync=bool(w.get('vsync', True))), runtime=ProjectRuntimeConfig(target_fps=int(r.get('target_fps', 120)), physics_fps=int(r.get('physics_fps', 60)), gravity=float(r.get('gravity', 980.0)), gravity_3d=float(r.get('gravity_3d', -9.81)), debug_overlay=bool(r.get('debug_overlay', False)), debug_collisions=bool(r.get('debug_collisions', False)), profiler_overlay=bool(r.get('profiler_overlay', False)), background_color=(int(bg[0]), int(bg[1]), int(bg[2]))), build=ProjectBuildConfig(product_name=str(b.get('product_name', payload.get('name') or root.name)), version=str(b.get('version', '0.1.0')), company=str(b.get('company', 'VVittox')), onefile=bool(b.get('onefile', False)), debug_console=bool(b.get('debug_console', False)), clean_build=bool(b.get('clean_build', True)), scenes=scenes), editor=ProjectEditorConfig(autosave_enabled=bool(e.get('autosave_enabled', True)), autosave_seconds=max(10, int(e.get('autosave_seconds', 60))), recovery_keep=max(1, int(e.get('recovery_keep', 10))), grid_size=max(1, int(e.get('grid_size', 16))), show_collision_shapes=bool(e.get('show_collision_shapes', True))), input_map={str(k): [str(x) for x in v] for k, v in dict(input_map).items()}, tags=[str(x) for x in payload.get('tags', ['Untagged', 'Player', 'Enemy', 'Collectible', 'UI'])], layers=[str(x) for x in payload.get('layers', ['Default'] + [f'Layer {i}' for i in range(1, 32)])], enabled_plugins=[str(x) for x in payload.get('enabled_plugins', [])])
        cfg.ensure_build_scenes()
        return cfg

    @classmethod
    def create(cls, root: str | Path, name: str, resources_dir: str | Path | None=None, template: str='empty') -> 'ProjectConfig':
        root = Path(root).expanduser().resolve()
        root.mkdir(parents=True, exist_ok=True)
        for folder in ('scenes', 'assets', 'scripts', 'builds', 'assets/textures', 'assets/audio', 'assets/materials', 'assets/shaders', 'assets/prefabs', 'assets/tilesets', 'addons', '.vworks/imports', '.vworks/autosave'):
            (root / folder).mkdir(parents=True, exist_ok=True)
        cfg = cls(root=root, name=name.strip() or root.name)
        cfg.build.product_name = cfg.name
        cfg.build.scenes = [BuildScene(cfg.main_scene, True)]
        cfg.save()
        if not cfg.main_scene_path.exists():
            scene = Scene('Main')
            if template == '2d_starter':
                title = Label2D('Title', 'V Works Engine', font_size=34)
                title.position = Vector2(48, 44)
                scene.add_child(title)
                player = ColorRect2D('Player', Vector2(64, 64), (70, 155, 235))
                player.position = Vector2(180, 220)
                player.tag = 'Player'
                scene.add_child(player)
                ground = ColorRect2D('Ground', Vector2(720, 48), (70, 75, 88))
                ground.position = Vector2(60, 520)
                scene.add_child(ground)
                scene.add_child(Light2D('KeyLight'))
            elif template == 'platformer':
                title = Label2D('Hint', 'Platformer Template — A/D + Space', 24, (235, 235, 245))
                title.position = Vector2(30, 24)
                scene.add_child(title)
                player = CharacterBody2D('Player')
                player.position = Vector2(150, 180)
                player.tag = 'Player'
                player.collider.size = Vector2(42, 58)
                scene.add_child(player)
                visual = ColorRect2D('Visual', Vector2(42, 58), (75, 165, 245))
                player.add_child(visual)
                ground = StaticBody2D('Ground')
                ground.position = Vector2(50, 520)
                ground.collider.size = Vector2(900, 50)
                scene.add_child(ground)
                ground_visual = ColorRect2D('Visual', Vector2(900, 50), (65, 72, 86))
                ground.add_child(ground_visual)
                cam = Camera2DNode('Camera2D')
                cam.position = Vector2(420, 300)
                scene.add_child(cam)
                script = root / 'scripts' / 'player.py'
                script.write_text('from engine.scripting import VScript\nfrom engine.utils.vmath import Vector2\n\nclass Script(VScript):\n    def _process(self, delta):\n        inp=self.engine.input if self.engine else None\n        if not inp: return\n        speed=260\n        self.owner.velocity.x=(1 if inp.action_pressed("ui_right") else 0)-(1 if inp.action_pressed("ui_left") else 0)\n        self.owner.velocity.x*=speed\n        if self.owner.on_ground and inp.action_just_pressed("ui_accept"):\n            self.owner.velocity.y=-430\n', encoding='utf-8')
                player.script_path = 'scripts/player.py'
            elif template == 'top_down':
                title = Label2D('Hint', 'Top Down Template — WASD', 24, (235, 235, 245))
                title.position = Vector2(30, 24)
                scene.add_child(title)
                player = CharacterBody2D('Player')
                player.position = Vector2(300, 260)
                player.tag = 'Player'
                player.collider.size = Vector2(48, 48)
                scene.add_child(player)
                player.add_child(ColorRect2D('Visual', Vector2(48, 48), (80, 180, 245)))
                cam = Camera2DNode('Camera2D')
                cam.position = Vector2(400, 300)
                scene.add_child(cam)
                script = root / 'scripts' / 'player.py'
                script.write_text('from engine.scripting import VScript\nfrom engine.utils.vmath import Vector2\n\nclass Script(VScript):\n    def _process(self, delta):\n        inp=self.engine.input if self.engine else None\n        if not inp: return\n        x=(1 if inp.action_pressed("ui_right") else 0)-(1 if inp.action_pressed("ui_left") else 0)\n        y=(1 if inp.action_pressed("ui_down") else 0)-(1 if inp.action_pressed("ui_up") else 0)\n        v=Vector2(x,y); self.owner.velocity=v.normalized*220 if v.length else Vector2()\n', encoding='utf-8')
                player.script_path = 'scripts/player.py'
            elif template == 'ui_app':
                canvas = CanvasLayer('UI')
                scene.add_child(canvas)
                panel = UIPanel('Panel')
                panel.set_anchor_preset('full_rect')
                panel.offset_left = 24
                panel.offset_top = 24
                panel.offset_right = -24
                panel.offset_bottom = -24
                canvas.add_child(panel)
                label = UILabel('Title', 'V Works UI App')
                label.anchor_left = 0.5
                label.anchor_top = 0.5
                label.anchor_right = 0.5
                label.anchor_bottom = 0.5
                label.offset_left = -120
                label.offset_top = -30
                label.offset_right = 120
                label.offset_bottom = 30
                label.font_size = 32
                panel.add_child(label)
            elif template == '3d_starter':
                env = WorldEnvironment3D('WorldEnvironment3D')
                env.ambient_energy = 0.28
                env.fog_enabled = False
                env.sky_enabled = True
                env.sky_top_color = (28, 42, 72)
                env.sky_bottom_color = (145, 185, 225)
                scene.add_child(env)
                light = DirectionalLight3D('DirectionalLight3D')
                light.rotation = Vector3(-0.7, -0.5, 0.0)
                scene.add_child(light)
                fill = PointLight3D('PointLight3D')
                fill.position = Vector3(2.5, 2.5, 2.5)
                fill.color = (120, 180, 255)
                fill.energy = 1.3
                fill.range = 9.0
                scene.add_child(fill)
                camera = Camera3DNode('Camera3D')
                camera.position = Vector3(0.0, 3.0, 7.0)
                camera.rotation = Vector3(-0.32, 0.0, 0.0)
                scene.add_child(camera)
                floor_body = StaticBody3D('FloorBody')
                floor_body.position = Vector3(0.0, -0.25, 0.0)
                floor_body.collider.size = Vector3(10.0, 0.5, 10.0)
                floor = MeshInstance3D('Floor', 'cube')
                floor.size = Vector3(10.0, 0.5, 10.0)
                floor.color = (70, 78, 92)
                floor_body.add_child(floor)
                scene.add_child(floor_body)
                cube_body = RigidBody3D('CubeBody')
                cube_body.position = Vector3(-1.5, 3.0, 0.0)
                cube_body.collider.size = Vector3(1.6, 1.6, 1.6)
                cube = MeshInstance3D('Cube', 'cube')
                cube.size = Vector3(1.6, 1.6, 1.6)
                cube.color = (80, 160, 240)
                cube_body.add_child(cube)
                scene.add_child(cube_body)
                sphere = MeshInstance3D('Sphere', 'sphere')
                sphere.position = Vector3(1.5, 1.0, 0.0)
                sphere.size = Vector3(1.7, 1.7, 1.7)
                sphere.color = (240, 125, 90)
                scene.add_child(sphere)
                marker = Marker3D('SpawnPoint')
                marker.position = Vector3(0.0, 0.5, 2.0)
                scene.add_child(marker)
                ray = RayCast3D('GroundRay')
                ray.position = Vector3(0.0, 2.0, 0.0)
                ray.target_position = Vector3(0.0, -5.0, 0.0)
                scene.add_child(ray)
            elif template == 'tilemap':
                tilemap = TileMap2D('WorldTileMap')
                tilemap.debug_grid = True
                for y in range(8):
                    for x in range(14):
                        if y in (0, 7) or x in (0, 13):
                            tilemap.set_tile(x, y, 1)
                tilemap.position = Vector2(64, 80)
                scene.add_child(tilemap)
                hint = Label2D('Hint', 'TileMap Template — select TileMap2D and open TileMap panel', 20, (235, 235, 245))
                hint.position = Vector2(32, 28)
                scene.add_child(hint)
            save_scene(scene, cfg.main_scene_path)
        if resources_dir is not None:
            resources = Path(resources_dir)
            for filename in ('vworks_icon.png', 'vworks_icon.ico'):
                src = resources / filename
                if src.exists():
                    dst = root / ('icon.png' if src.suffix.lower() == '.png' else 'icon.ico')
                    if not dst.exists():
                        shutil.copy2(src, dst)
        return cfg

    @classmethod
    def load_or_create(cls, root: str | Path, resources_dir: str | Path | None=None) -> 'ProjectConfig':
        root = Path(root).resolve()
        project_file = root / PROJECT_FILE
        if project_file.exists():
            return cls.load(project_file)
        cfg = cls.create(root, root.name or 'V Works Project', resources_dir)
        legacy = root / 'main.vscene'
        if legacy.exists():
            cfg.main_scene = 'main.vscene'
            cfg.build.scenes = [BuildScene('main.vscene', True)]
            cfg.save()
        return cfg
