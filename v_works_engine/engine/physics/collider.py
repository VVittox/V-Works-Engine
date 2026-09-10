from __future__ import annotations
from dataclasses import dataclass, field
from typing import Tuple
from ..utils.vmath import Vector2

@dataclass
class AABBCollider:
    size: Vector2 = field(default_factory=lambda: Vector2(32, 32))
    offset: Vector2 = field(default_factory=Vector2)
    enabled: bool = True
    is_trigger: bool = False

    def bounds(self, position: Vector2) -> Tuple[float, float, float, float]:
        x = position.x + self.offset.x
        y = position.y + self.offset.y
        return (x, y, x + self.size.x, y + self.size.y)

    def overlaps(self, position: Vector2, other: 'AABBCollider', other_position: Vector2) -> bool:
        a = self.bounds(position)
        b = other.bounds(other_position)
        return a[0] < b[2] and a[2] > b[0] and (a[1] < b[3]) and (a[3] > b[1])
