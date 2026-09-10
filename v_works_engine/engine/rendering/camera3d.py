from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from ..utils.vmath import Vector3, rotate_euler

@dataclass
class Camera3D:
    position: Vector3 = field(default_factory=lambda: Vector3(0.0, 2.0, 6.0))
    rotation: Vector3 = field(default_factory=Vector3)
    fov: float = 70.0
    near: float = 0.05
    far: float = 2000.0
    orthographic: bool = False
    ortho_size: float = 10.0
    enabled: bool = True
    cull_mask: int = 0xFFFFFFFF
    source_node: Any = None

    def basis(self) -> tuple[Vector3, Vector3, Vector3]:
        source = self.source_node
        if source is not None and all(hasattr(source, name) for name in ('global_up', 'global_forward')):
            forward = source.global_forward.normalized
            up_hint = source.global_up.normalized
        else:
            forward = rotate_euler(Vector3.FORWARD(), self.rotation).normalized
            up_hint = rotate_euler(Vector3.UP(), self.rotation).normalized
        right = forward.cross(up_hint).normalized
        if not right.length:
            right = rotate_euler(Vector3.RIGHT(), self.rotation).normalized
        up = right.cross(forward).normalized
        return right, up, forward

    def world_to_view(self, point: Vector3) -> Vector3:
        right, up, forward = self.basis()
        rel = point - self.position
        return Vector3(rel.dot(right), rel.dot(up), -rel.dot(forward))
