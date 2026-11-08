from __future__ import annotations
from dataclasses import dataclass, field
from ..utils.vmath import Vector3

@dataclass
class AABB3DCollider:
    size: Vector3 = field(default_factory=lambda: Vector3(1.0, 1.0, 1.0))
    offset: Vector3 = field(default_factory=Vector3)
    enabled: bool = True
    is_trigger: bool = False

    def bounds(self, position: Vector3):
        c = position + self.offset
        h = self.size * 0.5
        return (c.x - h.x, c.y - h.y, c.z - h.z, c.x + h.x, c.y + h.y, c.z + h.z)

    def overlaps(self, position: Vector3, other: 'AABB3DCollider', other_position: Vector3) -> bool:
        a = self.bounds(position)
        b = other.bounds(other_position)
        return a[0] < b[3] and a[3] > b[0] and a[1] < b[4] and a[4] > b[1] and a[2] < b[5] and a[5] > b[2]
