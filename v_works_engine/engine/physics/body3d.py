from __future__ import annotations
from ..scene.node import Node3D
from ..utils.vmath import Vector3
from .body import BodyType
from .collider3d import AABB3DCollider

class PhysicsBody3D(Node3D):
    def __init__(self, name: str='PhysicsBody3D', body_type: BodyType=BodyType.DYNAMIC) -> None:
        super().__init__(name)
        self.body_type = body_type
        self.velocity = Vector3()
        self.acceleration = Vector3()
        self.mass = 1.0
        self.gravity_scale = 1.0
        self.restitution = 0.0
        self.friction = 0.2
        self.collider = AABB3DCollider()
        self.collision_layer = 1
        self.collision_mask = 4294967295
        self.on_floor = False
        self.signals.add('body_entered', 'body_exited')

    def apply_force(self, force: Vector3) -> None:
        if self.body_type is BodyType.DYNAMIC and self.mass > 0:
            self.acceleration = self.acceleration + force / self.mass

    def apply_impulse(self, impulse: Vector3) -> None:
        if self.body_type is BodyType.DYNAMIC and self.mass > 0:
            self.velocity = self.velocity + impulse / self.mass

class StaticBody3D(PhysicsBody3D):
    def __init__(self, name: str='StaticBody3D') -> None:
        super().__init__(name, BodyType.STATIC)

class RigidBody3D(PhysicsBody3D):
    def __init__(self, name: str='RigidBody3D') -> None:
        super().__init__(name, BodyType.DYNAMIC)

class CharacterBody3D(PhysicsBody3D):
    def __init__(self, name: str='CharacterBody3D') -> None:
        super().__init__(name, BodyType.KINEMATIC)

    def move_and_slide(self, delta: float) -> None:
        self.position = self.position + self.velocity * delta


class Area3D(StaticBody3D):
    def __init__(self, name: str='Area3D') -> None:
        super().__init__(name)
        self.collider.is_trigger = True
