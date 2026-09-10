from __future__ import annotations
from pathlib import Path
from typing import Dict, Iterable, Tuple
import json
from ..utils.vmath import Vector2, Vector3
from .camera import Camera2D
from .camera3d import Camera3D
from .mesh3d import Mesh3D
from .texture import Texture

class PygameRenderer:

    def __init__(self, window_settings, project_root: str | Path | None=None) -> None:
        try:
            import pygame
        except ImportError as exc:
            raise RuntimeError('Pygame is required. Install with: pip install -r requirements.txt') from exc
        self.pygame = pygame
        self.project_root = Path(project_root).resolve() if project_root else Path.cwd().resolve()
        pygame.init()
        flags = 0
        if window_settings.fullscreen:
            flags |= pygame.FULLSCREEN
        if window_settings.borderless:
            flags |= pygame.NOFRAME
        if window_settings.resizable:
            flags |= pygame.RESIZABLE
        size = (window_settings.width, window_settings.height)
        try:
            self.screen = pygame.display.set_mode(size, flags, vsync=1 if window_settings.vsync else 0)
        except (TypeError, pygame.error):
            self.screen = pygame.display.set_mode(size, flags)
        pygame.display.set_caption(window_settings.title)
        if window_settings.window_icon:
            try:
                pygame.display.set_icon(pygame.image.load(window_settings.window_icon))
            except (pygame.error, FileNotFoundError):
                pass
        self.camera = Camera2D()
        self.camera3d = Camera3D()
        self._triangles3d: list[tuple[float, list[tuple[int, int]], tuple[int, int, int], bool]] = []
        self._mesh3d_cache: Dict[tuple, Mesh3D] = {}
        self._light3d_direction = Vector3(-0.4, -1.0, -0.6).normalized
        self._light3d_color = (255, 244, 220)
        self._light3d_energy = 1.0
        self._ambient3d_color = (255, 255, 255)
        self._ambient3d_energy = 0.22
        self._fog3d_enabled = False
        self._fog3d_color = (100, 120, 145)
        self._fog3d_near = 20.0
        self._fog3d_far = 100.0
        self._sky3d_enabled = False
        self._sky3d_top_color = (35, 50, 82)
        self._sky3d_bottom_color = (145, 185, 225)
        self._point_lights3d: list[dict] = []
        self._spot_lights3d: list[dict] = []
        self._font_cache: Dict[Tuple[str, int], object] = {}
        self._image_cache: Dict[str, object] = {}
        self._resource_cache: Dict[str, dict] = {}

    @property
    def size(self) -> Vector2:
        w, h = self.screen.get_size()
        return Vector2(float(w), float(h))

    def resolve_asset(self, path: str | Path) -> str:
        if not path:
            return ''
        p = Path(path)
        if not p.is_absolute():
            p = self.project_root / p
        return str(p.resolve())

    def _point(self, p: Vector2, world: bool=True) -> Tuple[int, int]:
        q = self.camera.world_to_screen(p, self.size) if world else p
        return (int(round(q.x)), int(round(q.y)))

    def clear(self, color: Tuple[int, int, int]) -> None:
        self._triangles3d.clear()
        self.screen.fill(color)

    def present(self) -> None:
        self.pygame.display.flip()

    def draw_rect(self, position: Vector2, size: Vector2, color=(255, 255, 255), width: int=0, world: bool=True) -> None:
        p = self.camera.world_to_screen(position, self.size) if world else position
        z = self.camera.zoom if world and self.camera.enabled else 1.0
        rect = self.pygame.Rect(round(p.x), round(p.y), round(size.x * z), round(size.y * z))
        self.pygame.draw.rect(self.screen, color, rect, width)

    def draw_circle(self, position: Vector2, radius: float, color=(255, 255, 255), width: int=0, world: bool=True) -> None:
        z = self.camera.zoom if world and self.camera.enabled else 1.0
        self.pygame.draw.circle(self.screen, color, self._point(position, world), max(1, round(radius * z)), width)

    def draw_rect_alpha(self, position: Vector2, size: Vector2, color=(255, 255, 255, 128), world: bool=True) -> None:
        p = self.camera.world_to_screen(position, self.size) if world else position
        z = self.camera.zoom if world and self.camera.enabled else 1.0
        w, h = (max(1, round(size.x * z)), max(1, round(size.y * z)))
        surf = self.pygame.Surface((w, h), self.pygame.SRCALPHA)
        surf.fill(tuple(color))
        self.screen.blit(surf, (round(p.x), round(p.y)))

    def draw_circle_alpha(self, position: Vector2, radius: float, color=(255, 255, 255, 128), world: bool=True) -> None:
        z = self.camera.zoom if world and self.camera.enabled else 1.0
        r = max(1, round(radius * z))
        surf = self.pygame.Surface((r * 2 + 2, r * 2 + 2), self.pygame.SRCALPHA)
        self.pygame.draw.circle(surf, tuple(color), (r + 1, r + 1), r)
        point = self._point(position, world)
        self.screen.blit(surf, (point[0] - r - 1, point[1] - r - 1))

    def draw_light(self, position: Vector2, radius: float, color=(255, 230, 180), energy: float=1.0, softness: float=0.7) -> None:
        z = self.camera.zoom if self.camera.enabled else 1.0
        r = max(2, round(radius * z))
        surf = self.pygame.Surface((r * 2, r * 2), self.pygame.SRCALPHA)
        rings = max(8, min(64, round(16 + softness * 32)))
        for i in range(rings, 0, -1):
            t = i / rings
            rr = max(1, round(r * t))
            alpha = max(0, min(255, round(255 * energy * (1 - t) * 0.22)))
            self.pygame.draw.circle(surf, (*color[:3], alpha), (r, r), rr)
        point = self._point(position, True)
        self.screen.blit(surf, (point[0] - r, point[1] - r), special_flags=self.pygame.BLEND_RGBA_ADD)

    def draw_screen_modulate(self, color=(255, 255, 255, 255)) -> None:
        overlay = self.pygame.Surface(self.screen.get_size(), self.pygame.SRCALPHA)
        overlay.fill(tuple(color))
        self.screen.blit(overlay, (0, 0), special_flags=self.pygame.BLEND_RGBA_MULT)

    def draw_line(self, a: Vector2, b: Vector2, color=(255, 255, 255), width: int=1, world: bool=True) -> None:
        self.pygame.draw.line(self.screen, color, self._point(a, world), self._point(b, world), width)

    def draw_polygon(self, points: Iterable[Vector2], color=(255, 255, 255), width: int=0, world: bool=True) -> None:
        self.pygame.draw.polygon(self.screen, color, [self._point(p, world) for p in points], width)

    def draw_texture(self, texture: Texture, position: Vector2, world: bool=True) -> None:
        p = self.camera.world_to_screen(position, self.size) if world else position
        surface = texture.surface
        if world and self.camera.enabled and (self.camera.zoom != 1.0):
            w = max(1, round(texture.width * self.camera.zoom))
            h = max(1, round(texture.height * self.camera.zoom))
            surface = self.pygame.transform.smoothscale(surface, (w, h))
        self.screen.blit(surface, (round(p.x), round(p.y)))

    def _image(self, path: str):
        resolved = self.resolve_asset(path)
        surface = self._image_cache.get(resolved)
        if surface is None:
            surface = self.pygame.image.load(resolved).convert_alpha()
            self._image_cache[resolved] = surface
        return surface

    def _resource_data(self, path: str) -> dict:
        if not path:
            return {}
        resolved = self.resolve_asset(path)
        if resolved not in self._resource_cache:
            try:
                payload = json.loads(Path(resolved).read_text(encoding='utf-8'))
                self._resource_cache[resolved] = dict(payload.get('data', {})) if payload.get('format') == 'vworks_resource' else {}
            except Exception:
                self._resource_cache[resolved] = {}
        return self._resource_cache[resolved]

    def _apply_material(self, surface, material_path: str):
        data = self._resource_data(material_path)
        if not data:
            return (surface, 'alpha')
        result = surface.copy()
        preset = str(data.get('shader_preset', data.get('preset', 'none'))).lower()
        shader_path = str(data.get('shader', '') or '')
        if shader_path:
            shader = self._resource_data(shader_path)
            preset = str(shader.get('preset', preset)).lower()
        if preset == 'grayscale' and hasattr(self.pygame.transform, 'grayscale'):
            result = self.pygame.transform.grayscale(result)
        elif preset == 'invert':
            inv = self.pygame.Surface(result.get_size(), self.pygame.SRCALPHA)
            inv.fill((255, 255, 255, 255))
            inv.blit(result, (0, 0), special_flags=self.pygame.BLEND_RGB_SUB)
            result = inv
        elif preset == 'pixelate':
            px = max(1, int(dict(data.get('params', {})).get('pixel_size', 4)))
            w = max(1, result.get_width() // px)
            h = max(1, result.get_height() // px)
            result = self.pygame.transform.scale(self.pygame.transform.scale(result, (w, h)), result.get_size())
        tint = list(data.get('tint', [255, 255, 255, 255]))
        tint = (tint + [255] * 4)[:4]
        if tuple(tint) != (255, 255, 255, 255):
            result.fill(tuple(tint), special_flags=self.pygame.BLEND_RGBA_MULT)
        return (result, str(data.get('blend_mode', 'alpha')).lower())

    def draw_atlas_tile(self, path: str, tile_index: int, columns: int, tile_size: Vector2, position: Vector2, scale: Vector2 | None=None, margin: int=0, spacing: int=0, world: bool=True) -> None:
        try:
            source = self._image(path)
        except (FileNotFoundError, self.pygame.error):
            self.draw_rect(position, tile_size, (220, 70, 110), 2, world)
            return
        tw, th = (max(1, int(tile_size.x)), max(1, int(tile_size.y)))
        cols = max(1, int(columns))
        idx = max(0, int(tile_index))
        col = idx % cols
        row = idx // cols
        x = margin + col * (tw + spacing)
        y = margin + row * (th + spacing)
        if x + tw > source.get_width() or y + th > source.get_height():
            self.draw_rect(position, tile_size, (220, 70, 110), 2, world)
            return
        surf = source.subsurface(self.pygame.Rect(x, y, tw, th)).copy()
        scale = scale or Vector2(1, 1)
        cam = self.camera.zoom if world and self.camera.enabled else 1.0
        target = (max(1, round(tw * abs(scale.x) * cam)), max(1, round(th * abs(scale.y) * cam)))
        if target != surf.get_size():
            surf = self.pygame.transform.scale(surf, target)
        p = self.camera.world_to_screen(position, self.size) if world else position
        self.screen.blit(surf, (round(p.x), round(p.y)))

    def draw_image_path(self, path: str, position: Vector2, scale: Vector2 | None=None, rotation: float=0.0, centered: bool=True, flip_h: bool=False, flip_v: bool=False, opacity: float=1.0, world: bool=True, material_path: str='') -> None:
        try:
            surface = self._image(path)
        except (FileNotFoundError, self.pygame.error):
            self.draw_rect(position, Vector2(48, 48), (220, 70, 110), 2, world)
            self.draw_line(position, position + Vector2(48, 48), (220, 70, 110), 2, world)
            return
        scale = scale or Vector2(1, 1)
        cam_zoom = self.camera.zoom if world and self.camera.enabled else 1.0
        sx, sy = (abs(scale.x) * cam_zoom, abs(scale.y) * cam_zoom)
        target = (max(1, round(surface.get_width() * sx)), max(1, round(surface.get_height() * sy)))
        if target != surface.get_size():
            surface = self.pygame.transform.smoothscale(surface, target)
        fh = flip_h ^ (scale.x < 0)
        fv = flip_v ^ (scale.y < 0)
        if fh or fv:
            surface = self.pygame.transform.flip(surface, fh, fv)
        if rotation:
            surface = self.pygame.transform.rotate(surface, -rotation * 57.29577951308232)
        blend_mode = 'alpha'
        if material_path:
            surface, blend_mode = self._apply_material(surface, material_path)
        if opacity < 0.999:
            surface = surface.copy()
            surface.set_alpha(max(0, min(255, round(opacity * 255))))
        p = self.camera.world_to_screen(position, self.size) if world else position
        rect = surface.get_rect()
        if centered:
            rect.center = (round(p.x), round(p.y))
        else:
            rect.topleft = (round(p.x), round(p.y))
        flags = self.pygame.BLEND_RGBA_ADD if blend_mode == 'add' else self.pygame.BLEND_RGBA_MULT if blend_mode == 'multiply' else 0
        self.screen.blit(surface, rect, special_flags=flags)

    def draw_text(self, text: str, position: Vector2, size: int=20, color=(240, 240, 240), font_name: str='', world: bool=False) -> None:
        font_name = self.resolve_asset(font_name) if font_name else ''
        key = (font_name, size)
        font = self._font_cache.get(key)
        if font is None:
            font = self.pygame.font.Font(font_name or None, size)
            self._font_cache[key] = font
        surface = font.render(str(text), True, color)
        self.screen.blit(surface, self._point(position, world))


    def set_directional_light_3d(self, direction: Vector3, color=(255, 244, 220), energy: float=1.0, ambient: float=0.22) -> None:
        self._light3d_direction = direction.normalized if direction.length else Vector3(-0.4, -1.0, -0.6).normalized
        self._light3d_color = tuple(color[:3])
        self._light3d_energy = max(0.0, float(energy))
        self._ambient3d_energy = max(0.0, float(ambient))

    def set_environment_3d(self, ambient_color=(255, 255, 255), ambient_energy: float=0.22, fog_enabled: bool=False, fog_color=(100, 120, 145), fog_near: float=20.0, fog_far: float=100.0, sky_enabled: bool=False, sky_top_color=(35, 50, 82), sky_bottom_color=(145, 185, 225)) -> None:
        self._ambient3d_color = tuple(ambient_color[:3])
        self._ambient3d_energy = max(0.0, float(ambient_energy))
        self._fog3d_enabled = bool(fog_enabled)
        self._fog3d_color = tuple(fog_color[:3])
        self._fog3d_near = max(0.0, float(fog_near))
        self._fog3d_far = max(self._fog3d_near + 0.001, float(fog_far))
        self._sky3d_enabled = bool(sky_enabled)
        self._sky3d_top_color = tuple(sky_top_color[:3])
        self._sky3d_bottom_color = tuple(sky_bottom_color[:3])

    def prepare_scene_3d(self, root) -> None:
        from ..scene.three_d import Camera3DNode, DirectionalLight3D, PointLight3D, SpotLight3D, WorldEnvironment3D
        self._point_lights3d.clear()
        self._spot_lights3d.clear()
        self._light3d_direction = Vector3(-0.4, -1.0, -0.6).normalized
        self._light3d_color = (255, 244, 220)
        self._light3d_energy = 1.0
        self._ambient3d_color = (255, 255, 255)
        self._ambient3d_energy = 0.22
        self._fog3d_enabled = False
        self._fog3d_color = (100, 120, 145)
        self._fog3d_near = 20.0
        self._fog3d_far = 100.0
        self._sky3d_enabled = False
        self.camera3d.source_node = None
        self.camera3d.position = Vector3(0.0, 2.0, 6.0)
        self.camera3d.rotation = Vector3()
        self.camera3d.fov = 70.0
        self.camera3d.near = 0.05
        self.camera3d.far = 2000.0
        self.camera3d.orthographic = False
        self.camera3d.ortho_size = 10.0
        self.camera3d.cull_mask = 0xFFFFFFFF
        self.camera3d.enabled = True
        camera_node = next((n for n in root.walk() if isinstance(n, Camera3DNode) and n.current and n.visible), None)
        if camera_node is not None:
            camera_node.sync_renderer(self)
        else:
            self.camera3d.source_node = None
        environment = next((n for n in root.walk() if isinstance(n, WorldEnvironment3D) and n.visible), None)
        if environment is not None:
            self.set_environment_3d(
                environment.ambient_color,
                environment.ambient_energy,
                environment.fog_enabled,
                environment.fog_color,
                environment.fog_near,
                environment.fog_far,
                environment.sky_enabled,
                environment.sky_top_color,
                environment.sky_bottom_color,
            )
        directional = next((n for n in root.walk() if isinstance(n, DirectionalLight3D) and n.enabled and n.visible), None)
        if directional is not None:
            self.set_directional_light_3d(directional.direction, directional.color, directional.energy, directional.ambient)
        for node in root.walk():
            if isinstance(node, SpotLight3D) and node.enabled and node.visible:
                self._spot_lights3d.append({
                    'position': node.global_position,
                    'direction': node.direction,
                    'color': tuple(node.color[:3]),
                    'energy': max(0.0, float(node.energy)),
                    'range': max(0.001, float(node.range)),
                    'attenuation': max(0.01, float(node.attenuation)),
                    'angle': max(1.0, min(179.0, float(node.spot_angle))),
                    'softness': max(0.0, min(1.0, float(node.edge_softness))),
                })
            elif isinstance(node, PointLight3D) and node.enabled and node.visible:
                self._point_lights3d.append({
                    'position': node.global_position,
                    'color': tuple(node.color[:3]),
                    'energy': max(0.0, float(node.energy)),
                    'range': max(0.001, float(node.range)),
                    'attenuation': max(0.01, float(node.attenuation)),
                })
        if self._sky3d_enabled:
            self._draw_sky_3d()

    def _draw_sky_3d(self) -> None:
        w, h = self.screen.get_size()
        if h <= 0:
            return
        for y in range(h):
            t = y / max(1, h - 1)
            color = self._mix_color(self._sky3d_top_color, self._sky3d_bottom_color, t)
            self.pygame.draw.line(self.screen, color, (0, y), (w, y))

    def _mesh3d(self, primitive: str, segments: int, rings: int) -> Mesh3D:
        key = (str(primitive).lower(), int(segments), int(rings))
        mesh = self._mesh3d_cache.get(key)
        if mesh is None:
            mesh = Mesh3D.from_primitive(key[0], key[1], key[2])
            self._mesh3d_cache[key] = mesh
        return mesh

    def _camera_space_3d(self, point: Vector3) -> Vector3:
        return self.camera3d.world_to_view(point)

    def _project_view_3d(self, view: Vector3) -> tuple[float, float, float] | None:
        depth = -view.z
        cam = self.camera3d
        if depth < cam.near or depth > cam.far:
            return None
        w, h = self.screen.get_size()
        if cam.orthographic:
            scale = h / max(0.001, cam.ortho_size)
            return (w * 0.5 + view.x * scale, h * 0.5 - view.y * scale, depth)
        focal = (h * 0.5) / max(0.001, __import__('math').tan(__import__('math').radians(cam.fov) * 0.5))
        return (w * 0.5 + view.x * focal / depth, h * 0.5 - view.y * focal / depth, depth)

    def project_3d(self, point: Vector3) -> tuple[float, float, float] | None:
        return self._project_view_3d(self._camera_space_3d(point))

    @staticmethod
    def _mix_color(a, b, t: float):
        t = max(0.0, min(1.0, t))
        return tuple(max(0, min(255, round(a[i] * (1.0 - t) + b[i] * t))) for i in range(3))

    @staticmethod
    def _clip_depth_plane(points: list[Vector3], depth: float, keep_nearer: bool) -> list[Vector3]:
        if not points:
            return []
        boundary_z = -depth
        def inside(p: Vector3) -> bool:
            return p.z >= boundary_z if keep_nearer else p.z <= boundary_z
        output = []
        prev = points[-1]
        prev_inside = inside(prev)
        for current in points:
            current_inside = inside(current)
            if current_inside != prev_inside:
                denom = current.z - prev.z
                if abs(denom) > 1e-12:
                    t = (boundary_z - prev.z) / denom
                    output.append(prev.lerp(current, t))
            if current_inside:
                output.append(current)
            prev = current
            prev_inside = current_inside
        return output

    def _clip_camera_polygon(self, points: list[Vector3]) -> list[Vector3]:
        points = self._clip_depth_plane(points, self.camera3d.near, False)
        points = self._clip_depth_plane(points, self.camera3d.far, True)
        return points

    def _light_face_3d(self, base_color, normal: Vector3, center: Vector3, shaded: bool, receive_light: bool=True):
        if not shaded or not receive_light:
            return tuple(base_color[:3])
        factors = [(self._ambient3d_color[i] / 255.0) * self._ambient3d_energy for i in range(3)]
        directional = max(0.0, normal.dot(-self._light3d_direction)) if normal.length else 0.0
        for i in range(3):
            factors[i] += (self._light3d_color[i] / 255.0) * directional * self._light3d_energy
        for light in self._point_lights3d:
            delta = light['position'] - center
            distance = delta.length
            if distance <= 1e-9 or distance > light['range']:
                continue
            direction = delta / distance
            lambert = max(0.0, normal.dot(direction))
            falloff = max(0.0, 1.0 - distance / light['range']) ** light['attenuation']
            for i in range(3):
                factors[i] += (light['color'][i] / 255.0) * lambert * falloff * light['energy']
        import math
        for light in self._spot_lights3d:
            delta = center - light['position']
            distance = delta.length
            if distance <= 1e-9 or distance > light['range']:
                continue
            from_light = delta / distance
            cone = max(-1.0, min(1.0, light['direction'].dot(from_light)))
            angle = math.degrees(math.acos(cone))
            half = light['angle'] * 0.5
            if angle > half:
                continue
            edge_start = half * (1.0 - light['softness'])
            cone_factor = 1.0 if angle <= edge_start else max(0.0, (half - angle) / max(0.001, half - edge_start))
            lambert = max(0.0, normal.dot(-from_light))
            falloff = max(0.0, 1.0 - distance / light['range']) ** light['attenuation']
            for i in range(3):
                factors[i] += (light['color'][i] / 255.0) * lambert * falloff * cone_factor * light['energy']
        return tuple(max(0, min(255, round(base_color[i] * min(2.0, factors[i])))) for i in range(3))

    def queue_mesh_3d(self, node) -> None:
        if not (self.camera3d.cull_mask & (1 << max(0, min(31, int(getattr(node, 'render_layer', 0)))))):
            return
        mesh_path = str(getattr(node, 'mesh_path', '') or '')
        if mesh_path:
            resolved = self.resolve_asset(mesh_path)
            try:
                stamp = Path(resolved).stat().st_mtime_ns
                key = ('obj', resolved, stamp)
                mesh = self._mesh3d_cache.get(key)
                if mesh is None:
                    mesh = Mesh3D.from_file(resolved)
                    self._mesh3d_cache[key] = mesh
            except Exception:
                mesh = self._mesh3d(getattr(node, 'primitive', 'cube'), getattr(node, 'segments', 14), getattr(node, 'rings', 9))
        else:
            mesh = self._mesh3d(getattr(node, 'primitive', 'cube'), getattr(node, 'segments', 14), getattr(node, 'rings', 9))
        size = getattr(node, 'size', Vector3(1, 1, 1))
        world_vertices = [node.to_global(Vector3(v.x * size.x, v.y * size.y, v.z * size.z)) for v in mesh.vertices]
        base_color = tuple(getattr(node, 'color', (110, 170, 235))[:3])
        wire = bool(getattr(node, 'wireframe', False))
        shaded = bool(getattr(node, 'shaded', True))
        double_sided = bool(getattr(node, 'double_sided', True))
        receive_light = bool(getattr(node, 'receive_light', True))
        for face in mesh.faces:
            if len(face) < 3:
                continue
            points3 = [world_vertices[i] for i in face]
            normal = (points3[1] - points3[0]).cross(points3[2] - points3[0]).normalized
            center = Vector3(
                sum(p.x for p in points3) / len(points3),
                sum(p.y for p in points3) / len(points3),
                sum(p.z for p in points3) / len(points3),
            )
            if not double_sided:
                to_camera = (self.camera3d.position - center).normalized
                if normal.dot(to_camera) <= 0.0:
                    continue
            view_points = [self._camera_space_3d(v) for v in points3]
            clipped = self._clip_camera_polygon(view_points)
            if len(clipped) < 3:
                continue
            projected = [self._project_view_3d(v) for v in clipped]
            if any(p is None for p in projected):
                continue
            pp = [p for p in projected if p is not None]
            screen_points = [(round(p[0]), round(p[1])) for p in pp]
            color = self._light_face_3d(base_color, normal, center, shaded, receive_light)
            depth = sum(p[2] for p in pp) / len(pp)
            if self._fog3d_enabled:
                fog_t = (depth - self._fog3d_near) / max(0.001, self._fog3d_far - self._fog3d_near)
                color = self._mix_color(color, self._fog3d_color, fog_t)
            self._triangles3d.append((depth, screen_points, color, wire))

    def queue_box_3d(self, node, offset: Vector3, size: Vector3, color=(80, 230, 120)) -> None:
        mesh = Mesh3D.cube()
        world_vertices = [node.to_global(offset + Vector3(v.x * size.x, v.y * size.y, v.z * size.z)) for v in mesh.vertices]
        for face in mesh.faces:
            points3 = [world_vertices[i] for i in face]
            clipped = self._clip_camera_polygon([self._camera_space_3d(v) for v in points3])
            if len(clipped) < 3:
                continue
            projected = [self._project_view_3d(v) for v in clipped]
            if any(p is None for p in projected):
                continue
            pp = [p for p in projected if p is not None]
            self._triangles3d.append((sum(p[2] for p in pp) / len(pp), [(round(p[0]), round(p[1])) for p in pp], tuple(color[:3]), True))

    def flush_3d(self) -> None:
        if not self._triangles3d:
            return
        self._triangles3d.sort(key=lambda item: item[0], reverse=True)
        for _, points, color, wire in self._triangles3d:
            if len(points) < 3:
                continue
            if wire:
                self.pygame.draw.polygon(self.screen, color, points, 1)
            else:
                self.pygame.draw.polygon(self.screen, color, points, 0)
                self.pygame.draw.polygon(self.screen, tuple(max(0, c - 35) for c in color), points, 1)
        self._triangles3d.clear()

    def shutdown(self) -> None:
        self._image_cache.clear()
        self._resource_cache.clear()
        self._font_cache.clear()
        self._mesh3d_cache.clear()
        self._triangles3d.clear()
        self.pygame.display.quit()
        self.pygame.quit()
