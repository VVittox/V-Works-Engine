from __future__ import annotations
from pathlib import Path
from ..utils.vmath import Vector2
from .node import Node2D

class ColorRect2D(Node2D):

    def __init__(self, name: str='ColorRect2D', size: Vector2 | None=None, color=(86, 156, 214)) -> None:
        super().__init__(name)
        self.size = size or Vector2(96.0, 64.0)
        self.color = tuple(color)

    def _draw(self, renderer) -> None:
        if self.visible:
            gp = self.global_position
            gs = self.global_scale
            gr = self.global_rotation
            if abs(gr) < 1e-09:
                renderer.draw_rect(gp, self.size * gs, self.color)
            else:
                corners = [gp, gp + Vector2(self.size.x * gs.x, 0).rotated(gr), gp + Vector2(self.size.x * gs.x, self.size.y * gs.y).rotated(gr), gp + Vector2(0, self.size.y * gs.y).rotated(gr)]
                renderer.draw_polygon(corners, self.color)

class Sprite2D(Node2D):

    def __init__(self, name: str='Sprite2D', texture_path: str='') -> None:
        super().__init__(name)
        self.texture_path = texture_path
        self.centered = True
        self.flip_h = False
        self.flip_v = False
        self.opacity = 1.0

    def _draw(self, renderer) -> None:
        if self.visible and self.texture_path:
            renderer.draw_image_path(self.texture_path, self.global_position, scale=self.global_scale, rotation=self.global_rotation, centered=self.centered, flip_h=self.flip_h, flip_v=self.flip_v, opacity=self.opacity, material_path=self.material_path)

class Label2D(Node2D):

    def __init__(self, name: str='Label2D', text: str='Label', font_size: int=24, color=(240, 240, 245)) -> None:
        super().__init__(name)
        self.text = text
        self.font_size = int(font_size)
        self.color = tuple(color)
        self.font_path = ''

    def _draw(self, renderer) -> None:
        if self.visible:
            renderer.draw_text(self.text, self.global_position, size=max(6, self.font_size), color=self.color, font_name=renderer.resolve_asset(self.font_path) if self.font_path else '', world=True)

class Camera2DNode(Node2D):

    def __init__(self, name: str='Camera2D') -> None:
        super().__init__(name)
        self.current = True
        self.zoom = 1.0

    def _process(self, delta: float) -> None:
        if not self.current:
            return
        tree = self.get_tree()
        engine = getattr(tree, 'engine', None) if tree else None
        renderer = getattr(engine, 'renderer', None) if engine else None
        if renderer is not None:
            renderer.camera.enabled = True
            renderer.camera.position = self.global_position
            renderer.camera.zoom = max(0.01, float(self.zoom))

class CollisionRect2D(Node2D):

    def __init__(self, name: str='CollisionRect2D', size: Vector2 | None=None) -> None:
        super().__init__(name)
        self.size = size or Vector2(64.0, 64.0)
        self.is_trigger = False
        self.debug_visible = False

    def _physics_process(self, delta: float) -> None:
        try:
            from ..physics.body import PhysicsBody2D
        except Exception:
            return
        if isinstance(self.parent, PhysicsBody2D):
            self.parent.collider.size = Vector2(self.size.x * abs(self.scale.x), self.size.y * abs(self.scale.y))
            self.parent.collider.offset = Vector2(self.position.x, self.position.y)
            self.parent.collider.is_trigger = bool(self.is_trigger)

    def _draw(self, renderer) -> None:
        if self.debug_visible:
            renderer.draw_rect(self.global_position, self.size * self.global_scale, (80, 235, 120), width=2)
