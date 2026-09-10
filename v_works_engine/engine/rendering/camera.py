from __future__ import annotations
from dataclasses import dataclass, field
from ..utils.vmath import Vector2

@dataclass
class Camera2D:
    position: Vector2 = field(default_factory=Vector2)
    zoom: float = 1.0
    enabled: bool = False

    def world_to_screen(self, point: Vector2, viewport_size: Vector2) -> Vector2:
        if not self.enabled:
            return Vector2(point.x, point.y)
        z = max(0.0001, self.zoom)
        return Vector2((point.x - self.position.x) * z + viewport_size.x * 0.5, (point.y - self.position.y) * z + viewport_size.y * 0.5)

    def screen_to_world(self, point: Vector2, viewport_size: Vector2) -> Vector2:
        if not self.enabled:
            return Vector2(point.x, point.y)
        z = max(0.0001, self.zoom)
        return Vector2((point.x - viewport_size.x * 0.5) / z + self.position.x, (point.y - viewport_size.y * 0.5) / z + self.position.y)
