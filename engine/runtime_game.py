from __future__ import annotations
import sys
from pathlib import Path
from .core.project_config import ProjectConfig
from .core.settings import EngineSettings
from .core.engine import Engine
from .scene.serialization import load_scene
from .scripting import attach_project_scripts, connect_scene_signals

def settings_from_project(cfg: ProjectConfig) -> EngineSettings:
    settings = EngineSettings()
    settings.window.title = cfg.name
    settings.window.width = cfg.window.width
    settings.window.height = cfg.window.height
    settings.window.fullscreen = cfg.window.fullscreen
    settings.window.borderless = cfg.window.borderless
    settings.window.resizable = cfg.window.resizable
    settings.window.vsync = cfg.window.vsync
    settings.target_fps = cfg.runtime.target_fps
    settings.physics_fps = cfg.runtime.physics_fps
    settings.physics.gravity = cfg.runtime.gravity
    settings.physics.gravity_3d = cfg.runtime.gravity_3d
    settings.background_color = cfg.runtime.background_color
    settings.custom['project_root'] = str(cfg.root)
    settings.custom['render_backend'] = cfg.runtime.render_backend
    settings.custom['input_map'] = cfg.input_map
    settings.custom['debug_overlay'] = cfg.runtime.debug_overlay or cfg.runtime.profiler_overlay
    settings.custom['debug_collisions'] = cfg.runtime.debug_collisions
    settings.custom['build_scenes'] = [s.path for s in cfg.enabled_build_scenes]
    if cfg.icon_path.exists():
        settings.window.window_icon = str(cfg.icon_path)
    return settings

def _load_runtime_scene(cfg: ProjectConfig, request: str | int):
    path = cfg.scene_path(request)
    if not path.exists():
        raise FileNotFoundError(f'Scene not found: {path}')
    scene = load_scene(path)
    attach_project_scripts(scene, cfg.root, strict=cfg.runtime.strict_scripts)
    connect_scene_signals(scene, strict=cfg.runtime.strict_scripts)
    return scene

def run_project(project_dir: str | Path) -> int:
    cfg = ProjectConfig.load(project_dir)
    if not cfg.main_scene_path.exists():
        raise FileNotFoundError(f'Main scene not found: {cfg.main_scene_path}')
    engine = Engine(settings_from_project(cfg))
    engine.scene_loader = lambda request: _load_runtime_scene(cfg, request)
    scene = _load_runtime_scene(cfg, cfg.main_scene)
    engine.run(scene)
    return 0

def bundled_project_dir() -> Path:
    base = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
    return base / 'game_data'

def run_bundled_game() -> int:
    return run_project(bundled_project_dir())
if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python -m engine.runtime_game <project-folder>')
        raise SystemExit(2)
    raise SystemExit(run_project(sys.argv[1]))
