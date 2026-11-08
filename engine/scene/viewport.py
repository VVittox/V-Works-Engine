from __future__ import annotations
from dataclasses import dataclass
from ..utils.vmath import Vector2

@dataclass
class Viewport:
    width: int
    height: int

    @property
    def size(self) -> Vector2:
        return Vector2(float(self.width), float(self.height))

    @property
    def center(self) -> Vector2:
        return Vector2(self.width * 0.5, self.height * 0.5)
