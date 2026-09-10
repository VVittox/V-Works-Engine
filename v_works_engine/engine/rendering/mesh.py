from __future__ import annotations
from dataclasses import dataclass, field
from typing import List
from ..utils.vmath import Vector2

@dataclass
class Mesh2D:
    vertices: List[Vector2] = field(default_factory=list)

    @classmethod
    def rectangle(cls, width: float, height: float) -> 'Mesh2D':
        return cls([Vector2(0, 0), Vector2(width, 0), Vector2(width, height), Vector2(0, height)])
