from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Tuple

@dataclass
class Material:
    color: Tuple[int, int, int, int] = (255, 255, 255, 255)
    texture: Optional[object] = None
    layer: int = 0
    unlit: bool = True
