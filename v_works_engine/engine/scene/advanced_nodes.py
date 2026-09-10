from __future__ import annotations
import heapq
import math
import random
from dataclasses import dataclass
from typing import Iterable
from ..utils.vmath import Vector2
from .node import Node, Node2D

class TileMap2D(Node2D):

    def __init__(self, name: str='TileMap2D') -> None:
        super().__init__(name)
        self.texture_path = ''
        self.tile_size = Vector2(32, 32)
        self.atlas_columns = 8
        self.margin = 0
        self.spacing = 0
        self.tiles: dict[str, int] = {}
        self.collision_tiles: set[int] = set()
        self.debug_grid = False

    @staticmethod
    def _key(x: int, y: int) -> str:
        return f'{int(x)},{int(y)}'

    def set_tile(self, x: int, y: int, tile: int) -> None:
        key = self._key(x, y)
        if int(tile) < 0:
            self.tiles.pop(key, None)
        else:
            self.tiles[key] = int(tile)

    def erase_tile(self, x: int, y: int) -> None:
        self.tiles.pop(self._key(x, y), None)

    def get_tile(self, x: int, y: int) -> int:
        return int(self.tiles.get(self._key(x, y), -1))

    def iter_tiles(self) -> Iterable[tuple[int, int, int]]:
        for key, tile in self.tiles.items():
            try:
                x, y = key.split(',', 1)
                yield (int(x), int(y), int(tile))
            except (ValueError, TypeError):
                continue

    def world_to_cell(self, point: Vector2) -> tuple[int, int]:
        gp = self.global_position
        return (math.floor((point.x - gp.x) / max(1.0, self.tile_size.x)), math.floor((point.y - gp.y) / max(1.0, self.tile_size.y)))

    def cell_to_world(self, x: int, y: int) -> Vector2:
        return self.global_position + Vector2(x * self.tile_size.x, y * self.tile_size.y)

    def _draw(self, renderer) -> None:
        if not self.visible:
            return
        for x, y, tile in self.iter_tiles():
            pos = self.cell_to_world(x, y)
            if self.texture_path:
                renderer.draw_atlas_tile(self.texture_path, tile, max(1, self.atlas_columns), self.tile_size, pos, scale=self.global_scale, margin=self.margin, spacing=self.spacing)
            else:
                hue = tile * 47 % 180
                renderer.draw_rect(pos, self.tile_size * self.global_scale, (70 + hue // 3, 90 + hue // 4, 125 + hue // 5))
            if self.debug_grid:
                renderer.draw_rect(pos, self.tile_size * self.global_scale, (95, 120, 145), width=1)

@dataclass
class _Particle:
    position: Vector2
    velocity: Vector2
    age: float
    lifetime: float
    size: float

class ParticleSystem2D(Node2D):

    def __init__(self, name: str='ParticleSystem2D') -> None:
        super().__init__(name)
        self.emitting = True
        self.amount = 128
        self.emission_rate = 40.0
        self.lifetime = 1.5
        self.speed_min = 40.0
        self.speed_max = 140.0
        self.direction = -90.0
        self.spread = 45.0
        self.gravity = Vector2(0, 90)
        self.color_start = (255, 210, 100, 255)
        self.color_end = (255, 80, 60, 0)
        self.size_start = 5.0
        self.size_end = 1.0
        self.texture_path = ''
        self.local_coords = True
        self._particles: list[_Particle] = []
        self._spawn_accum = 0.0
        self._rng = random.Random(self.id * 7919)

    def restart(self) -> None:
        self._particles.clear()
        self._spawn_accum = 0.0
        self.emitting = True

    def _spawn(self) -> None:
        if len(self._particles) >= max(0, int(self.amount)):
            return
        angle = math.radians(self.direction + self._rng.uniform(-self.spread, self.spread))
        speed = self._rng.uniform(self.speed_min, self.speed_max)
        vel = Vector2(math.cos(angle) * speed, math.sin(angle) * speed)
        origin = Vector2() if self.local_coords else self.global_position
        self._particles.append(_Particle(origin, vel, 0.0, max(0.01, self.lifetime), self.size_start))

    def _process(self, delta: float) -> None:
        dt = min(max(0.0, float(delta)), 0.1)
        if self.emitting and self.emission_rate > 0:
            self._spawn_accum += dt * self.emission_rate
            count = min(int(self._spawn_accum), max(0, self.amount - len(self._particles)))
            self._spawn_accum -= count
            for _ in range(count):
                self._spawn()
        alive: list[_Particle] = []
        for p in self._particles:
            p.age += dt
            if p.age >= p.lifetime:
                continue
            p.velocity = p.velocity + self.gravity * dt
            p.position = p.position + p.velocity * dt
            t = p.age / p.lifetime
            p.size = self.size_start + (self.size_end - self.size_start) * t
            alive.append(p)
        self._particles = alive

    def _draw(self, renderer) -> None:
        if not self.visible:
            return
        for p in self._particles:
            t = min(1.0, p.age / max(0.001, p.lifetime))
            color = tuple((int(self.color_start[i] + (self.color_end[i] - self.color_start[i]) * t) for i in range(4)))
            pos = p.position + self.global_position if self.local_coords else p.position
            if self.texture_path:
                renderer.draw_image_path(self.texture_path, pos, scale=Vector2(max(0.02, p.size / 16), max(0.02, p.size / 16)), opacity=color[3] / 255.0)
            else:
                renderer.draw_circle_alpha(pos, max(1.0, p.size), color)

class CanvasLayer(Node):

    def __init__(self, name: str='CanvasLayer') -> None:
        super().__init__(name)
        self.layer = 0
        self.visible = True

class Control(Node2D):

    def __init__(self, name: str='Control') -> None:
        super().__init__(name)
        self.size = Vector2(160, 64)
        self.anchor_left = 0.0
        self.anchor_top = 0.0
        self.anchor_right = 0.0
        self.anchor_bottom = 0.0
        self.offset_left = 0.0
        self.offset_top = 0.0
        self.offset_right = 160.0
        self.offset_bottom = 64.0
        self.mouse_filter = 'stop'

    def set_anchor_preset(self, preset: str) -> None:
        presets = {'top_left': (0, 0, 0, 0), 'top_right': (1, 0, 1, 0), 'bottom_left': (0, 1, 0, 1), 'bottom_right': (1, 1, 1, 1), 'center': (0.5, 0.5, 0.5, 0.5), 'full_rect': (0, 0, 1, 1), 'top_wide': (0, 0, 1, 0), 'bottom_wide': (0, 1, 1, 1)}
        a = presets.get(preset, presets['top_left'])
        self.anchor_left, self.anchor_top, self.anchor_right, self.anchor_bottom = map(float, a)

    def resolved_rect(self, viewport_size: Vector2) -> tuple[Vector2, Vector2]:
        parent_size = viewport_size
        base = Vector2()
        if isinstance(self.parent, Control):
            _, parent_size = self.parent.resolved_rect(viewport_size)
            base = self.parent.resolved_rect(viewport_size)[0]
        left = base.x + parent_size.x * self.anchor_left + self.offset_left
        top = base.y + parent_size.y * self.anchor_top + self.offset_top
        right = base.x + parent_size.x * self.anchor_right + self.offset_right
        bottom = base.y + parent_size.y * self.anchor_bottom + self.offset_bottom
        return (Vector2(left, top), Vector2(max(0, right - left), max(0, bottom - top)))

class UIPanel(Control):

    def __init__(self, name: str='UIPanel') -> None:
        super().__init__(name)
        self.color = (40, 44, 54, 230)
        self.border_color = (74, 82, 100, 255)
        self.border_width = 0

    def _draw(self, renderer) -> None:
        if not self.visible:
            return
        pos, size = self.resolved_rect(renderer.size)
        renderer.draw_rect_alpha(pos, size, self.color, world=False)
        if self.border_width:
            renderer.draw_rect(pos, size, self.border_color[:3], width=self.border_width, world=False)

class UILabel(Control):

    def __init__(self, name: str='UILabel', text: str='Label') -> None:
        super().__init__(name)
        self.text = text
        self.font_size = 20
        self.color = (245, 245, 248, 255)
        self.align = 'left'

    def _draw(self, renderer) -> None:
        if not self.visible:
            return
        pos, _ = self.resolved_rect(renderer.size)
        renderer.draw_text(self.text, pos, self.font_size, self.color[:3], world=False)

class Light2D(Node2D):

    def __init__(self, name: str='Light2D') -> None:
        super().__init__(name)
        self.radius = 180.0
        self.energy = 1.0
        self.color = (255, 225, 170)
        self.softness = 0.7
        self.enabled = True

    def _draw(self, renderer) -> None:
        if self.visible and self.enabled:
            renderer.draw_light(self.global_position, self.radius * max(abs(self.global_scale.x), abs(self.global_scale.y)), self.color, self.energy, self.softness)

class CanvasModulate(Node):

    def __init__(self, name: str='CanvasModulate') -> None:
        super().__init__(name)
        self.color = (255, 255, 255, 255)

    def _draw(self, renderer) -> None:
        renderer.draw_screen_modulate(self.color)

class Navigation2D(Node2D):

    def __init__(self, name: str='Navigation2D') -> None:
        super().__init__(name)
        self.cell_size = 32.0
        self.width = 40
        self.height = 24
        self.allow_diagonal = False
        self.blocked: set[str] = set()
        self.debug_visible = False

    @staticmethod
    def _key(x: int, y: int) -> str:
        return f'{x},{y}'

    def set_blocked(self, x: int, y: int, blocked: bool=True) -> None:
        key = self._key(int(x), int(y))
        self.blocked.add(key) if blocked else self.blocked.discard(key)

    def is_blocked(self, x: int, y: int) -> bool:
        return self._key(int(x), int(y)) in self.blocked

    def world_to_cell(self, p: Vector2) -> tuple[int, int]:
        g = self.global_position
        s = max(1.0, self.cell_size)
        return (int(math.floor((p.x - g.x) / s)), int(math.floor((p.y - g.y) / s)))

    def cell_to_world(self, x: int, y: int) -> Vector2:
        s = max(1.0, self.cell_size)
        return self.global_position + Vector2((x + 0.5) * s, (y + 0.5) * s)

    def find_path(self, start: Vector2, goal: Vector2) -> list[Vector2]:
        start_c = self.world_to_cell(start)
        goal_c = self.world_to_cell(goal)

        def valid(c):
            return 0 <= c[0] < self.width and 0 <= c[1] < self.height and (not self.is_blocked(*c))
        if not valid(start_c) or not valid(goal_c):
            return []
        dirs = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        if self.allow_diagonal:
            dirs += [(1, 1), (1, -1), (-1, 1), (-1, -1)]
        open_heap = [(0.0, start_c)]
        came = {}
        gscore = {start_c: 0.0}
        visited = set()
        while open_heap:
            _, cur = heapq.heappop(open_heap)
            if cur in visited:
                continue
            visited.add(cur)
            if cur == goal_c:
                break
            for dx, dy in dirs:
                nxt = (cur[0] + dx, cur[1] + dy)
                if not valid(nxt):
                    continue
                ng = gscore[cur] + (1.4142 if dx and dy else 1.0)
                if ng < gscore.get(nxt, 1e+30):
                    gscore[nxt] = ng
                    came[nxt] = cur
                    h = abs(nxt[0] - goal_c[0]) + abs(nxt[1] - goal_c[1])
                    heapq.heappush(open_heap, (ng + h, nxt))
        if goal_c != start_c and goal_c not in came:
            return []
        cells = [goal_c]
        cur = goal_c
        while cur != start_c:
            cur = came[cur]
            cells.append(cur)
        cells.reverse()
        return [self.cell_to_world(x, y) for x, y in cells]

    def _draw(self, renderer) -> None:
        if not self.debug_visible:
            return
        s = max(1.0, self.cell_size)
        for y in range(self.height):
            for x in range(self.width):
                pos = self.global_position + Vector2(x * s, y * s)
                if self.is_blocked(x, y):
                    renderer.draw_rect_alpha(pos, Vector2(s, s), (220, 70, 90, 90))
                renderer.draw_rect(pos, Vector2(s, s), (70, 115, 110), width=1)

class NavigationAgent2D(Node2D):

    def __init__(self, name: str='NavigationAgent2D') -> None:
        super().__init__(name)
        self.target_position = Vector2()
        self.speed = 120.0
        self.enabled = True
        self.arrival_distance = 4.0
        self._path: list[Vector2] = []
        self._path_index = 0
        self.signals.add('navigation_finished')

    def _navigation(self) -> Navigation2D | None:
        root: Node = self
        while root.parent is not None:
            root = root.parent
        return next((n for n in root.walk() if isinstance(n, Navigation2D)), None)

    def set_target(self, target: Vector2) -> None:
        self.target_position = Vector2(target.x, target.y)
        nav = self._navigation()
        self._path = nav.find_path(self.global_position, target) if nav else [target]
        self._path_index = 1 if len(self._path) > 1 else 0

    def _process(self, delta: float) -> None:
        if not self.enabled:
            return
        if not self._path:
            self.set_target(self.target_position)
        if not self._path or self._path_index >= len(self._path):
            return
        target = self._path[self._path_index]
        d = target - self.global_position
        dist = d.length
        if dist <= self.arrival_distance:
            self._path_index += 1
            if self._path_index >= len(self._path):
                self.signals.emit('navigation_finished')
            return
        step = min(dist, max(0.0, self.speed * delta))
        self.position = self.position + d.normalized * step

    def _draw(self, renderer) -> None:
        if len(self._path) > 1:
            for a, b in zip(self._path, self._path[1:]):
                renderer.draw_line(a, b, (90, 230, 180), 2)
