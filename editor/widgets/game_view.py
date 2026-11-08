from __future__ import annotations
import math, time
from pathlib import Path
from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QImage, QKeyEvent, QLinearGradient, QPainter, QPen, QPixmap, QPolygonF
from PySide6.QtWidgets import QWidget
from engine.core.settings import EngineSettings
from engine.physics import PhysicsBody2D
from engine.physics.world import PhysicsWorld
from engine.scene import Camera2DNode, Camera3DNode, ColorRect2D, Label2D, MeshInstance3D, Node2D, Node3D, Scene, Sprite2D, TileMap2D, ParticleSystem2D, Light2D, Control, UIPanel, UILabel, Navigation2D, DirectionalLight3D, PointLight3D, SpotLight3D, WorldEnvironment3D
from engine.scene.scene_tree import SceneTree
from engine.scene.serialization import node_from_dict, node_to_dict
from engine.rendering.mesh3d import Mesh3D
from engine.scripting import attach_project_scripts, connect_scene_signals
from engine.utils.vmath import Vector2, Vector3

class _PreviewInput:

    def __init__(self, mapping):
        self.mapping = {k: {str(x).lower() for x in v} for k, v in mapping.items()}
        self.down = set()
        self.pressed = set()
        self.released = set()
        self.mouse_position = Vector2()
        self.mouse_pressed = set()
        self.mouse_down = set()
        self.mouse_released = set()

    def begin_frame(self):
        self.pressed.clear()
        self.released.clear()
        self.mouse_pressed.clear()
        self.mouse_released.clear()

    def _names(self, key):
        from PySide6.QtCore import Qt
        table = {Qt.Key_Left: 'left', Qt.Key_Right: 'right', Qt.Key_Up: 'up', Qt.Key_Down: 'down', Qt.Key_Space: 'space', Qt.Key_Return: 'return', Qt.Key_Enter: 'return', Qt.Key_Escape: 'escape'}
        if key in table:
            return [table[key]]
        if Qt.Key_A <= key <= Qt.Key_Z:
            return [chr(key).lower()]
        return [str(key)]

    def key_down(self, key):
        for n in self._names(key):
            if n not in self.down:
                self.pressed.add(n)
            self.down.add(n)

    def key_up(self, key):
        for n in self._names(key):
            self.down.discard(n)
            self.released.add(n)

    def is_action_pressed(self, name):
        return any((k in self.down for k in self.mapping.get(name, set())))

    def is_action_just_pressed(self, name):
        return any((k in self.pressed for k in self.mapping.get(name, set())))

    def is_action_just_released(self, name):
        return any((k in self.released for k in self.mapping.get(name, set())))
    action_pressed = is_action_pressed
    action_just_pressed = is_action_just_pressed
    action_just_released = is_action_just_released

    def get_axis(self, neg, pos):
        return float(self.is_action_pressed(pos)) - float(self.is_action_pressed(neg))

    def get_vector(self, l, r, u, d):
        v = Vector2(self.get_axis(l, r), self.get_axis(u, d))
        return v.normalized if v.length > 1 else v

class _PreviewEngine:

    def __init__(self, project):
        self.input = _PreviewInput(project.input_map)
        self.assets = None
        self.audio = None
        self.renderer = None
        self.project_root = project.root
        self.pending_scene = None

    def change_scene(self, scene):
        self.pending_scene = scene

class GameView(QWidget):
    profiler_updated = Signal(dict)
    state_changed = Signal(str)

    def __init__(self, project, parent=None):
        super().__init__(parent)
        self.project = project
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMinimumSize(520, 320)
        self.scene_source = None
        self.scene = None
        self.tree = None
        self.preview_engine = None
        self.physics = None
        self.playing = False
        self.paused = False
        self.debug_collisions = False
        self._pixmaps = {}
        self._meshes3d = {}
        self._last = time.perf_counter()
        self._accum = 0.0
        self._frames = 0
        self._fps_time = self._last
        self._fps = 0.0
        self._last_stats = {}
        self.runtime = None
        self.last_error = ''
        self.setMouseTracking(True)
        self.timer = QTimer(self)
        self.timer.setInterval(16)
        self.timer.timeout.connect(self._tick)

    def set_project(self, project):
        self.project = project

    def set_scene_source(self, scene):
        self.scene_source = scene
        self.update()

    def play(self):
        if self.scene_source is None:
            return
        self.stop()
        self.last_error = ''
        if getattr(self.project.runtime, 'preview_backend', 'legacy') == 'engine':
            from editor.runtime_preview import RuntimePreview
            self.runtime = RuntimePreview(self.project)
            try:
                self.runtime.start(self.scene_source)
            except Exception:
                self.runtime.stop()
                self.runtime = None
                raise
            self.preview_engine = self.runtime.engine
            self.tree = self.preview_engine.tree
            self.scene = self.preview_engine.current_scene
            self.physics = self.preview_engine.physics
            self.playing = True
            self.paused = False
            self._last = time.perf_counter()
            self._fps_time = self._last
            self._frames = 0
            self.timer.start()
            self.state_changed.emit('playing')
            self.setFocus()
            self.update()
            return
        self.scene = node_from_dict(node_to_dict(self.scene_source))
        if not isinstance(self.scene, Scene):
            return
        attach_project_scripts(self.scene, self.project.root)
        connect_scene_signals(self.scene)
        self.preview_engine = _PreviewEngine(self.project)
        self.tree = SceneTree(engine=self.preview_engine)
        self.tree.set_current_scene(self.scene)
        settings = EngineSettings().physics
        settings.gravity = self.project.runtime.gravity
        settings.gravity_3d = self.project.runtime.gravity_3d
        self.physics = PhysicsWorld(settings)
        self.playing = True
        self.paused = False
        self._last = time.perf_counter()
        self._accum = 0.0
        self.timer.start()
        self.state_changed.emit('playing')
        self.setFocus()
        self.update()

    def stop(self):
        self.timer.stop()
        if self.runtime is not None:
            self.runtime.stop()
            self.runtime = None
        self.playing = False
        self.paused = False
        self.scene = None
        self.tree = None
        self.preview_engine = None
        self.state_changed.emit('stopped')
        self.update()

    def toggle_pause(self):
        if not self.playing:
            return
        self.paused = not self.paused
        self.state_changed.emit('paused' if self.paused else 'playing')

    def step(self):
        if not self.playing:
            self.play()
        if self.playing:
            self.paused = True
            self._simulate(self.preview_engine.loop.fixed_delta if self.runtime is not None else 1 / 60)
            self.state_changed.emit('paused')
            self.update()

    def _simulate(self, dt):
        if self.runtime is not None:
            self.preview_engine.fps = self._fps
            self.preview_engine.debug_collisions = self.debug_collisions
            self.runtime.advance(dt)
            self.scene = self.preview_engine.current_scene
            self._last_stats.update(
                process_ms=self.preview_engine.profiler.avg('process'),
                physics_ms=self.preview_engine.profiler.avg('physics'),
                paint_ms=self.preview_engine.profiler.avg('draw'))
            if not self.preview_engine.running:
                self.stop()
            return
        if not self.tree or not self.physics:
            return
        t = time.perf_counter()
        self.tree.process(dt)
        process_ms = (time.perf_counter() - t) * 1000
        t = time.perf_counter()
        self.tree.physics_process(dt)
        self.physics.step(self.tree.root, dt)
        physics_ms = (time.perf_counter() - t) * 1000
        self._last_stats.update(process_ms=process_ms, physics_ms=physics_ms)

    def _tick(self):
        now = time.perf_counter()
        dt = min(0.1, now - self._last)
        self._last = now
        if not self.paused:
            try:
                self._simulate(dt)
            except Exception as exc:
                import traceback
                self.last_error = str(exc)
                traceback.print_exc()
                self.stop()
                self.state_changed.emit('error: ' + self.last_error)
        if self.preview_engine and self.runtime is None:
            self.preview_engine.input.begin_frame()
        self._frames += 1
        if now - self._fps_time >= 0.5:
            self._fps = self._frames / (now - self._fps_time)
            self._frames = 0
            self._fps_time = now
        self._last_stats.update(fps=self._fps, frame_ms=dt * 1000, nodes=sum((1 for _ in self.scene.walk())) if self.scene else 0)
        self.profiler_updated.emit(dict(self._last_stats))
        self.update()

    def keyPressEvent(self, e: QKeyEvent):
        if self.runtime is not None and not e.isAutoRepeat():
            self._runtime_key(e, True)
        elif self.preview_engine and (not e.isAutoRepeat()):
            self.preview_engine.input.key_down(e.key())
        super().keyPressEvent(e)

    def keyReleaseEvent(self, e: QKeyEvent):
        if self.runtime is not None and not e.isAutoRepeat():
            self._runtime_key(e, False)
        elif self.preview_engine and (not e.isAutoRepeat()):
            self.preview_engine.input.key_up(e.key())
        super().keyReleaseEvent(e)

    def _runtime_key(self, event, down):
        table = {Qt.Key_Left: 'left', Qt.Key_Right: 'right', Qt.Key_Up: 'up',
                 Qt.Key_Down: 'down', Qt.Key_Space: 'space', Qt.Key_Return: 'return',
                 Qt.Key_Enter: 'return', Qt.Key_Escape: 'escape', Qt.Key_Shift: 'left shift',
                 Qt.Key_Tab: 'tab'}
        name = table.get(event.key(), event.text().lower())
        code = self.preview_engine.input.key_code(name) if name else None
        if code is not None:
            pg = self.preview_engine.renderer.pygame
            self.runtime.event(pg.KEYDOWN if down else pg.KEYUP, key=code)

    def _runtime_mouse(self, event, kind):
        game, scale = self._game_rect()
        point = event.position()
        values = {'pos': ((point.x()-game.x())/scale, (point.y()-game.y())/scale)}
        pg = self.preview_engine.renderer.pygame
        if kind != pg.MOUSEMOTION:
            button = {Qt.LeftButton: 1, Qt.MiddleButton: 2, Qt.RightButton: 3}.get(event.button())
            if button is None:
                return
            values['button'] = button
        self.runtime.event(kind, **values)

    def mousePressEvent(self, event):
        if self.runtime is not None:
            self.setFocus()
            self._runtime_mouse(event, self.preview_engine.renderer.pygame.MOUSEBUTTONDOWN)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if self.runtime is not None:
            self._runtime_mouse(event, self.preview_engine.renderer.pygame.MOUSEBUTTONUP)
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        if self.runtime is not None:
            self._runtime_mouse(event, self.preview_engine.renderer.pygame.MOUSEMOTION)
        super().mouseMoveEvent(event)

    def focusOutEvent(self, event):
        if self.runtime is not None:
            self.runtime.event(self.preview_engine.renderer.pygame.WINDOWFOCUSLOST)
        super().focusOutEvent(event)

    def _resolve(self, text):
        p = Path(text)
        return p if p.is_absolute() else self.project.root / p

    def _pixmap(self, text):
        key = str(self._resolve(text).resolve())
        if key not in self._pixmaps:
            self._pixmaps[key] = QPixmap(key)
        return self._pixmaps[key] if not self._pixmaps[key].isNull() else None

    def _game_rect(self):
        gw, gh = (self.project.window.width, self.project.window.height)
        if self.runtime is not None and self.preview_engine.renderer is not None:
            size = self.preview_engine.renderer.size
            gw, gh = size.x, size.y
        scale = min(self.width() / gw, self.height() / gh)
        w = gw * scale
        h = gh * scale
        return (QRectF((self.width() - w) / 2, (self.height() - h) / 2, w, h), scale)

    def _camera(self):
        scene = self.scene if self.playing and self.scene else self.scene_source
        if not scene:
            return None
        return next((n for n in scene.walk() if isinstance(n, Camera2DNode) and n.current), None)

    def _camera3d(self, scene):
        return next((n for n in scene.walk() if isinstance(n, Camera3DNode) and n.current), None) if scene else None

    def _mesh3d(self, node):
        if node.mesh_path:
            path = Path(node.mesh_path)
            if not path.is_absolute():
                path = self.project.root / path
            try:
                key = (str(path.resolve()), path.stat().st_mtime_ns)
                mesh = self._meshes3d.get(key)
                if mesh is None:
                    mesh = Mesh3D.from_file(str(path))
                    self._meshes3d[key] = mesh
                return mesh
            except Exception:
                pass
        key = ('primitive', node.primitive, node.segments, node.rings)
        if key not in self._meshes3d:
            self._meshes3d[key] = Mesh3D.from_primitive(node.primitive, node.segments, node.rings)
        return self._meshes3d[key]

    def _view3d(self, point, camera):
        if camera:
            position = camera.global_position
            forward = camera.global_forward.normalized
            up_hint = camera.global_up.normalized
            right = forward.cross(up_hint).normalized
            if not right.length:
                right = camera.global_right.normalized
            up = right.cross(forward).normalized
        else:
            position = Vector3(0, 2, 6)
            right = Vector3.RIGHT()
            up = Vector3.UP()
            forward = Vector3.FORWARD()
        rel = point - position
        return Vector3(rel.dot(right), rel.dot(up), -rel.dot(forward))

    def _project_view3d(self, view, camera, game):
        fov = camera.fov if camera else 70.0
        near = camera.near if camera else 0.05
        far = camera.far if camera else 2000.0
        ortho = camera.orthographic if camera else False
        ortho_size = camera.ortho_size if camera else 10.0
        depth = -view.z
        if depth < near or depth > far:
            return None
        if ortho:
            factor = game.height() / max(0.001, ortho_size)
            return QPointF(game.center().x() + view.x * factor, game.center().y() - view.y * factor), depth
        focal = (game.height() * 0.5) / max(0.001, math.tan(math.radians(fov) * 0.5))
        return QPointF(game.center().x() + view.x * focal / depth, game.center().y() - view.y * focal / depth), depth

    def _project3d(self, point, camera, game):
        return self._project_view3d(self._view3d(point, camera), camera, game)

    @staticmethod
    def _clip_depth3d(points, depth, keep_nearer):
        if not points:
            return []
        boundary = -depth
        def inside(p):
            return p.z >= boundary if keep_nearer else p.z <= boundary
        out = []
        prev = points[-1]
        prev_in = inside(prev)
        for cur in points:
            cur_in = inside(cur)
            if cur_in != prev_in:
                dz = cur.z - prev.z
                if abs(dz) > 1e-12:
                    t = (boundary - prev.z) / dz
                    out.append(prev.lerp(cur, t))
            if cur_in:
                out.append(cur)
            prev, prev_in = cur, cur_in
        return out

    def _clip_camera3d(self, points, camera):
        near = camera.near if camera else 0.05
        far = camera.far if camera else 2000.0
        return self._clip_depth3d(self._clip_depth3d(points, near, False), far, True)

    def _draw_3d(self, painter, scene, game):
        meshes = [n for n in scene.walk() if isinstance(n, MeshInstance3D) and n.visible]
        env = next((n for n in scene.walk() if isinstance(n, WorldEnvironment3D) and n.visible), None)
        if env and env.sky_enabled:
            gradient = QLinearGradient(game.topLeft(), game.bottomLeft())
            gradient.setColorAt(0.0, QColor(*env.sky_top_color))
            gradient.setColorAt(1.0, QColor(*env.sky_bottom_color))
            painter.fillRect(game, gradient)
        if not meshes:
            return
        camera = self._camera3d(scene)
        light = next((n for n in scene.walk() if isinstance(n, DirectionalLight3D) and n.enabled and n.visible), None)
        points = [n for n in scene.walk() if isinstance(n, PointLight3D) and not isinstance(n, SpotLight3D) and n.enabled and n.visible]
        spots = [n for n in scene.walk() if isinstance(n, SpotLight3D) and n.enabled and n.visible]
        direction = Vector3(-0.4, -1, -0.6).normalized
        energy = 1.0
        ambient = env.ambient_energy if env else 0.25
        ambient_color = env.ambient_color if env else (255, 255, 255)
        light_color = (255, 244, 220)
        if light:
            direction = light.direction
            energy, ambient, light_color = light.energy, light.ambient if env is None else env.ambient_energy, light.color
        faces = []
        cull_mask = int(camera.cull_mask) if camera else 0xFFFFFFFF
        for node in meshes:
            if not (cull_mask & (1 << max(0, min(31, int(getattr(node, 'render_layer', 0)))))):
                continue
            mesh = self._mesh3d(node)
            size = node.size
            verts = [node.to_global(Vector3(v.x * size.x, v.y * size.y, v.z * size.z)) for v in mesh.vertices]
            for face in mesh.faces:
                if len(face) < 3:
                    continue
                world = [verts[i] for i in face]
                normal = (world[1] - world[0]).cross(world[2] - world[0]).normalized
                center = Vector3(sum(v.x for v in world) / len(world), sum(v.y for v in world) / len(world), sum(v.z for v in world) / len(world))
                if not node.double_sided:
                    camera_pos = camera.global_position if camera else Vector3(0, 2, 6)
                    if normal.dot((camera_pos - center).normalized) <= 0:
                        continue
                view = self._clip_camera3d([self._view3d(v, camera) for v in world], camera)
                if len(view) < 3:
                    continue
                projected = [self._project_view3d(v, camera, game) for v in view]
                if any(x is None for x in projected):
                    continue
                base = node.color
                if node.shaded and node.receive_light:
                    factors = [(ambient_color[i] / 255.0) * ambient for i in range(3)]
                    lambert = max(0.0, normal.dot(-direction)) if normal.length else 0.0
                    for i in range(3):
                        factors[i] += light_color[i] / 255.0 * lambert * energy
                    for local_light in points:
                        delta = local_light.global_position - center
                        dist = delta.length
                        if 1e-9 < dist <= local_light.range:
                            ld = delta / dist
                            lam = max(0.0, normal.dot(ld))
                            falloff = max(0.0, 1.0 - dist / max(0.001, local_light.range)) ** max(0.01, local_light.attenuation)
                            for i in range(3):
                                factors[i] += local_light.color[i] / 255.0 * lam * falloff * local_light.energy
                    for local_light in spots:
                        delta = center - local_light.global_position
                        dist = delta.length
                        if 1e-9 < dist <= local_light.range:
                            outward = delta / dist
                            cone = max(-1.0, min(1.0, local_light.direction.dot(outward)))
                            angle = math.degrees(math.acos(cone))
                            half = local_light.spot_angle * 0.5
                            if angle <= half:
                                edge = half * (1.0 - local_light.edge_softness)
                                cone_factor = 1.0 if angle <= edge else max(0.0, (half - angle) / max(0.001, half - edge))
                                lam = max(0.0, normal.dot(-outward))
                                falloff = max(0.0, 1.0 - dist / max(0.001, local_light.range)) ** max(0.01, local_light.attenuation)
                                for i in range(3):
                                    factors[i] += local_light.color[i] / 255.0 * lam * falloff * cone_factor * local_light.energy
                    color = tuple(max(0, min(255, round(base[i] * min(2.0, factors[i])))) for i in range(3))
                else:
                    color = base
                depth = sum(x[1] for x in projected) / len(projected)
                if env and env.fog_enabled:
                    t = max(0.0, min(1.0, (depth - env.fog_near) / max(0.001, env.fog_far - env.fog_near)))
                    color = tuple(round(color[i] * (1 - t) + env.fog_color[i] * t) for i in range(3))
                faces.append((depth, [x[0] for x in projected], color, node.wireframe))
        faces.sort(key=lambda x: x[0], reverse=True)
        for _, pts, color, wire in faces:
            painter.setPen(QPen(QColor(*(max(0, c - 30) for c in color)), 1))
            painter.setBrush(Qt.NoBrush if wire else QColor(*color))
            painter.drawPolygon(QPolygonF(pts))

    def _world(self, p: Vector2):
        rect, scale = self._game_rect()
        cam = self._camera()
        if cam:
            z = max(0.01, cam.zoom)
            x = (p.x - cam.global_position.x) * z + self.project.window.width * 0.5
            y = (p.y - cam.global_position.y) * z + self.project.window.height * 0.5
        else:
            x, y = (p.x, p.y)
        return QPointF(rect.x() + x * scale, rect.y() + y * scale)

    def paintEvent(self, event):
        t = time.perf_counter()
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.fillRect(self.rect(), QColor(20, 21, 25))
        game, scale = self._game_rect()
        bg = self.project.runtime.background_color
        if self.scene and self.scene.background_color:
            bg = self.scene.background_color
        p.fillRect(game, QColor(*bg))
        p.setClipRect(game)
        scene = self.scene if self.playing and self.scene else self.scene_source
        if self.runtime is not None and self.preview_engine.renderer is not None:
            renderer = self.preview_engine.renderer
            width, height = renderer.screen.get_size()
            raw = renderer.pygame.image.tobytes(renderer.screen, 'RGB')
            image = QImage(raw, width, height, width*3, QImage.Format.Format_RGB888)
            p.drawImage(game, image)
        elif scene:
            self._draw_3d(p, scene, game)
            nodes = [n for n in scene.walk() if isinstance(n, Node2D) and getattr(n, 'visible', True)]
            nodes.sort(key=lambda n: n.z_index)
            for n in nodes:
                self._draw_node(p, n, scale)
        p.setClipping(False)
        p.setPen(QPen(QColor(100, 105, 118), 1))
        p.drawRect(game)
        p.setPen(QColor(210, 214, 223))
        state = 'PLAY' if self.playing and (not self.paused) else 'PAUSED' if self.playing else 'GAME VIEW'
        p.drawText(12, 22, f'{state}  {self.project.window.width}×{self.project.window.height}  {self._fps:.1f} FPS')
        if self.last_error:
            p.setPen(QColor(255, 120, 120))
            p.drawText(12, 46, self.last_error)
        paint_ms = (time.perf_counter() - t) * 1000
        self._last_stats['paint_ms'] = paint_ms

    def _draw_node(self, p, n, scale):
        game, _game_scale = self._game_rect()
        pos = self._world(n.global_position)
        gs = n.global_scale
        cam = self._camera()
        cz = max(0.01, cam.zoom) if cam else 1.0
        s = scale * cz
        if isinstance(n, ColorRect2D):
            p.fillRect(QRectF(pos.x(), pos.y(), abs(n.size.x * gs.x * s), abs(n.size.y * gs.y * s)), QColor(*n.color))
        elif isinstance(n, Sprite2D):
            pm = self._pixmap(n.texture_path) if n.texture_path else None
            if pm:
                w = abs(pm.width() * gs.x * s)
                h = abs(pm.height() * gs.y * s)
                r = QRectF(pos.x() - w / 2 if n.centered else pos.x(), pos.y() - h / 2 if n.centered else pos.y(), w, h)
                p.save()
                p.setOpacity(max(0, min(1, n.opacity)))
                p.translate(r.center())
                p.rotate(math.degrees(n.global_rotation))
                p.drawPixmap(QRectF(-w / 2, -h / 2, w, h), pm, QRectF(pm.rect()))
                p.restore()
        elif isinstance(n, Label2D):
            font = p.font()
            font.setPointSize(max(6, round(n.font_size * s)))
            p.setFont(font)
            p.setPen(QColor(*n.color))
            p.drawText(pos, n.text)
        elif isinstance(n, TileMap2D):
            pm = self._pixmap(n.texture_path) if n.texture_path else None
            tw, th = (n.tile_size.x, n.tile_size.y)
            for x, y, tile in n.iter_tiles():
                q = self._world(n.cell_to_world(x, y))
                dst = QRectF(q.x(), q.y(), tw * abs(gs.x) * s, th * abs(gs.y) * s)
                if pm:
                    col = tile % max(1, n.atlas_columns)
                    row = tile // max(1, n.atlas_columns)
                    src = QRectF(n.margin + col * (tw + n.spacing), n.margin + row * (th + n.spacing), tw, th)
                    p.drawPixmap(dst, pm, src)
                else:
                    p.fillRect(dst, QColor(80 + tile * 31 % 120, 100, 145))
        elif isinstance(n, ParticleSystem2D):
            for part in getattr(n, '_particles', []):
                q = self._world(part.position + n.global_position if n.local_coords else part.position)
                r = max(1, part.size * s)
                p.setBrush(QColor(255, 165, 85, 180))
                p.setPen(Qt.NoPen)
                p.drawEllipse(q, r, r)
        elif isinstance(n, Light2D):
            r = n.radius * s
            p.setPen(QPen(QColor(*n.color, 100), 2))
            p.setBrush(QColor(*n.color, 30))
            p.drawEllipse(pos, r, r)
        elif isinstance(n, Navigation2D) and n.debug_visible:
            cell = n.cell_size * s
            p.setPen(QPen(QColor(60, 130, 110, 120), 1))
            for y in range(n.height):
                for x in range(n.width):
                    q = self._world(n.global_position + Vector2(x * n.cell_size, y * n.cell_size))
                    rr = QRectF(q.x(), q.y(), cell, cell)
                    p.drawRect(rr)
                    if n.is_blocked(x, y):
                        p.fillRect(rr, QColor(220, 70, 90, 80))
        elif isinstance(n, UIPanel):
            gp, size = n.resolved_rect(Vector2(self.project.window.width, self.project.window.height))
            q = QPointF(game.x() + gp.x * scale, game.y() + gp.y * scale)
            p.fillRect(QRectF(q.x(), q.y(), size.x * scale, size.y * scale), QColor(*n.color))
        elif isinstance(n, UILabel):
            gp, _ = n.resolved_rect(Vector2(self.project.window.width, self.project.window.height))
            q = QPointF(game.x() + gp.x * scale, game.y() + gp.y * scale)
            font = p.font()
            font.setPointSize(max(6, round(n.font_size * scale)))
            p.setFont(font)
            p.setPen(QColor(*n.color))
            p.drawText(q, n.text)
        if self.debug_collisions and isinstance(n, PhysicsBody2D):
            q = self._world(n.global_position + n.collider.offset)
            p.setPen(QPen(QColor(80, 230, 120), 2))
            p.setBrush(Qt.NoBrush)
            p.drawRect(QRectF(q.x(), q.y(), n.collider.size.x * s, n.collider.size.y * s))
