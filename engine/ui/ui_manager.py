from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple
from ..utils.vmath import Vector2

@dataclass
class UILabel:
    text: str
    position: Vector2
    font_size: int = 20
    color: Tuple[int, int, int] = (240, 240, 240)
    visible: bool = True

@dataclass
class UIButton:
    text: str
    position: Vector2
    size: Vector2
    on_click: Optional[Callable[[], None]] = None
    visible: bool = True

class UIManager:

    def __init__(self) -> None:
        self.labels: List[UILabel] = []
        self.buttons: List[UIButton] = []

    def add_label(self, label: UILabel) -> UILabel:
        self.labels.append(label)
        return label

    def add_button(self, button: UIButton) -> UIButton:
        self.buttons.append(button)
        return button

    def update(self, input_manager) -> None:
        if 1 not in input_manager.mouse_pressed:
            return
        p = input_manager.mouse_position
        for button in reversed(self.buttons):
            if not button.visible:
                continue
            if button.position.x <= p.x <= button.position.x + button.size.x and button.position.y <= p.y <= button.position.y + button.size.y:
                if button.on_click is not None:
                    button.on_click()
                break

    def draw(self, renderer) -> None:
        for label in self.labels:
            if label.visible:
                renderer.draw_text(label.text, label.position, label.font_size, label.color, world=False)
        for button in self.buttons:
            if not button.visible:
                continue
            renderer.draw_rect(button.position, button.size, (55, 61, 77), world=False)
            renderer.draw_text(button.text, button.position + Vector2(10, 7), 18, world=False)
