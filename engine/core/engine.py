from __future__ import annotations
from pathlib import Path
from typing import Callable, Optional
from .events import EventBus
from .loop import FixedTimestepLoop
from .settings import EngineSettings
from ..assets.asset_manager import AssetManager
from ..audio.audio_manager import AudioManager
from ..input.input_manager import InputManager
from ..physics.world import PhysicsWorld
from ..rendering.renderer import PygameRenderer
from ..scene.scene import Scene
from ..scene.scene_tree import SceneTree
from ..ui.ui_manager import UIManager
from ..utils.logger import VLogger, LogLevel
from ..utils.vmath import Vector2
from ..profiling import Profiler

class Engine:

    def __init__(self, settings: Optional[EngineSettings]=None) -> None:
        self.settings = settings or EngineSettings()
        self.logger = VLogger(LogLevel.DEBUG if self.settings.debug else LogLevel.INFO, 'Engine')
        self.events = EventBus()
        self.tree = SceneTree(engine=self)
        self.loop = FixedTimestepLoop(self.settings.physics_fps, self.settings.max_frame_delta)
        self.renderer = None
        self.input = None
        self.audio = None
        self.assets = None
        self.physics = PhysicsWorld(self.settings.physics)
        self.ui = UIManager()
        self.running = False
        self.delta = 0.0
        self.fps = 0.0
        self.project_root = Path(self.settings.custom.get('project_root', Path.cwd())).resolve()
        self.input_map = dict(self.settings.custom.get('input_map', {}))
        self.debug_overlay = bool(self.settings.custom.get('debug_overlay', False))
        self.debug_collisions = bool(self.settings.custom.get('debug_collisions', False))
        self.profiler = Profiler()
        self.build_scenes = list(self.settings.custom.get('build_scenes', []))
        self.scene_loader: Callable[[str | int], Scene] | None = None
        self._pending_scene: str | int | None = None

    @property
    def current_scene(self) -> Optional[Scene]:
        return self.tree.current_scene

    def set_scene(self, scene: Scene) -> Scene:
        self.physics.reset_contacts()
        if self.renderer is not None:
            self.renderer.camera.enabled = False
        return self.tree.set_current_scene(scene)

    def change_scene(self, scene: str | int) -> None:
        self._pending_scene = scene

    def _apply_scene_change(self) -> None:
        if self._pending_scene is None:
            return
        request, self._pending_scene = (self._pending_scene, None)
        if self.scene_loader is None:
            raise RuntimeError('No scene loader is configured for this engine')
        self.set_scene(self.scene_loader(request))
        self.events.emit('scene_changed', self.current_scene)

    def start(self) -> None:
        if self.renderer is not None:
            return
        self.renderer = PygameRenderer(self.settings.window, self.project_root,
                                       offscreen=bool(self.settings.custom.get('offscreen', False)),
                                       render_backend=self.settings.custom.get('render_backend', 'cpu'))
        self.input = InputManager(self.renderer.pygame)
        if self.input_map:
            self.input.configure_actions(self.input_map, replace=True)
        self.audio = AudioManager(self.renderer.pygame, self.settings.audio)
        self.assets = AssetManager(self.renderer, self.audio)
        self.loop.reset()
        self.logger.info('V Works Engine started')
        self.events.emit('engine_started', self)

    def stop(self) -> None:
        self.running = False

    def advance_frame(self, delta: float, events=(), *, render: bool=True) -> None:





        self.delta = min(max(float(delta), 0.0), self.settings.max_frame_delta)
        if self.input is not None:
            self.input.update(events)
            if self.input.quit_requested:
                self.stop()
                return
        self.loop.advance(self.delta, self._physics_tick, self._process_tick)
        if render and self.renderer is not None:
            self.draw_frame()

    def _physics_tick(self, delta: float) -> None:
        with self.profiler.measure('physics'):
            self.tree.physics_process(delta)
            self.physics.step(self.tree.root, delta)
            self.events.emit('physics_frame', delta)

    def _process_tick(self, delta: float) -> None:
        with self.profiler.measure('process'):
            self.tree.process(delta)
            if self.input is not None:
                self.ui.update(self.input)
            self._apply_scene_change()
            self.events.emit('process_frame', delta)

    def draw_frame(self) -> None:
        color = self.settings.background_color
        if self.current_scene and self.current_scene.background_color is not None:
            color = self.current_scene.background_color
        with self.profiler.measure('draw'):
            self.renderer.clear(color)
            self.tree.draw(self.renderer)
            self.ui.draw(self.renderer)
            if self.debug_collisions:
                from ..physics.body import PhysicsBody2D
                from ..physics.body3d import PhysicsBody3D
                for body in (n for n in self.tree.root.walk() if isinstance(n, PhysicsBody2D)
                             and n.is_enabled_in_tree and n.collider.enabled):
                    self.renderer.draw_rect(body.global_position + body.collider.offset,
                                            body.collider.size * body.global_scale,
                                            (80, 235, 120) if body.collider.is_trigger else (80, 180, 245), width=2)
                for body in (n for n in self.tree.root.walk() if isinstance(n, PhysicsBody3D)
                             and n.is_enabled_in_tree and n.collider.enabled):
                    self.renderer.queue_box_3d(body, body.collider.offset, body.collider.size,
                                              (235, 190, 80) if body.collider.is_trigger else (80, 235, 120))
                self.renderer.flush_3d()
            if self.debug_overlay:
                nodes = sum(1 for _ in self.tree.root.walk())
                self.renderer.draw_text(
                    f"FPS {self.fps:5.1f}   Nodes {nodes}   CPU P {self.profiler.avg('process'):.2f}ms "
                    f"Ph {self.profiler.avg('physics'):.2f}ms D {self.profiler.avg('draw'):.2f}ms "
                    f"3D {self.renderer.active_3d_backend}",
                    Vector2(10, 10), 18, (150, 230, 170), world=False)
            self.renderer.present()

    def run(self, scene: Optional[Scene]=None) -> None:

        self.start()
        if scene is not None:
            self.set_scene(scene)
        if self.current_scene is None:
            self.set_scene(Scene())
        pg = self.renderer.pygame
        clock = pg.time.Clock()
        self.running = True

        try:
            while self.running:
                limit = max(0, self.settings.target_fps)
                delta = clock.tick(limit) / 1000.0
                self.fps = clock.get_fps()
                self.advance_frame(delta, pg.event.get())
        finally:
            self.shutdown()

    def shutdown(self) -> None:
        self.running = False
        self.events.emit('engine_stopping', self)
        if self.current_scene is not None:
            self.tree.current_scene.remove_from_parent()
            self.tree.current_scene = None
        if self.assets is not None:
            self.assets.clear()
        if self.renderer is not None:
            self.renderer.shutdown()
        self.renderer = self.input = self.audio = self.assets = None
        self.logger.info('V Works Engine stopped')
