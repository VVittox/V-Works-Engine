from __future__ import annotations
from enum import Enum, auto
from ..scene.node import Node2D
from ..utils.vmath import Vector2
from .collider import AABBCollider

class BodyType(Enum):
    STATIC = auto()
    DYNAMIC = auto()
    KINEMATIC = auto()

class PhysicsBody2D(Node2D):

    def __init__(self, name: str='PhysicsBody2D', body_type: BodyType=BodyType.DYNAMIC) -> None:
        super().__init__(name)
        self.body_type = body_type
        self.velocity = Vector2()
        self.acceleration = Vector2()
        self.mass = 1.0
        self.gravity_scale = 1.0
        self.restitution = 0.0
        self.friction = 0.2
        self.collider = AABBCollider()
        self.collision_layer = 1
        self.collision_mask = 4294967295
        self.on_ground = False
        self.signals.add('body_entered', 'body_exited')

    def apply_force(self, force: Vector2) -> None:
        if self.body_type is BodyType.DYNAMIC and self.mass > 0:
            self.acceleration = self.acceleration + force / self.mass

    def apply_impulse(self, impulse: Vector2) -> None:
        if self.body_type is BodyType.DYNAMIC and self.mass > 0:
            self.velocity = self.velocity + impulse / self.mass

class StaticBody2D(PhysicsBody2D):

    def __init__(self, name: str='StaticBody2D') -> None:
        super().__init__(name, BodyType.STATIC)

class RigidBody2D(PhysicsBody2D):

    def __init__(self, name: str='RigidBody2D') -> None:
        super().__init__(name, BodyType.DYNAMIC)

class CharacterBody2D(PhysicsBody2D):

    def __init__(self, name: str='CharacterBody2D') -> None:
        super().__init__(name, BodyType.KINEMATIC)

    def move_and_slide(self, delta: float) -> None:
        self.position = self.position + self.velocity * delta


class Area2D(StaticBody2D):
    def __init__(self, name: str='Area2D') -> None:
        super().__init__(name)
        self.collider.is_trigger = True
