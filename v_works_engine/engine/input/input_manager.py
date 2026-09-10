from __future__ import annotations
from collections import defaultdict
from typing import Dict, Iterable, Set
from ..utils.vmath import Vector2

class InputManager:

    def __init__(self, pygame_module) -> None:
        self.pg = pygame_module
        self.keys_down: Set[int] = set()
        self.keys_pressed: Set[int] = set()
        self.keys_released: Set[int] = set()
        self.mouse_down: Set[int] = set()
        self.mouse_pressed: Set[int] = set()
        self.mouse_released: Set[int] = set()
        self.mouse_position = Vector2()
        self.quit_requested = False
        self.actions: Dict[str, Set[int]] = defaultdict(set)
        self._bind_defaults()

    def _bind_defaults(self) -> None:
        self.configure_actions({'ui_left': ['left', 'a'], 'ui_right': ['right', 'd'], 'ui_up': ['up', 'w'], 'ui_down': ['down', 's'], 'ui_accept': ['return', 'space'], 'ui_cancel': ['escape']}, replace=True)

    def key_code(self, key_name: str) -> int | None:
        text = str(key_name).strip().lower()
        aliases = {'enter': 'return', 'esc': 'escape', 'ctrl': 'left ctrl', 'shift': 'left shift'}
        text = aliases.get(text, text)
        try:
            return int(self.pg.key.key_code(text))
        except (ValueError, TypeError, AttributeError):
            attr = f"K_{text.replace(' ', '_')}"
            return getattr(self.pg, attr, None)

    def configure_actions(self, mapping: dict[str, list[str]], replace: bool=False) -> None:
        if replace:
            self.actions.clear()
        for name, names in mapping.items():
            if replace:
                self.actions[str(name)] = set()
            for key_name in names:
                code = self.key_code(key_name)
                if code is not None:
                    self.bind_action(str(name), code)

    def bind_action(self, name: str, *keys: int) -> None:
        self.actions[name].update(keys)

    def unbind_action(self, name: str, key: int | None=None) -> None:
        if key is None:
            self.actions.pop(name, None)
        else:
            self.actions[name].discard(key)

    def update(self, events: Iterable[object]) -> None:
        pg = self.pg
        self.keys_pressed.clear()
        self.keys_released.clear()
        self.mouse_pressed.clear()
        self.mouse_released.clear()
        self.quit_requested = False
        for event in events:
            if event.type == pg.QUIT:
                self.quit_requested = True
            elif event.type == pg.KEYDOWN:
                self.keys_down.add(event.key)
                self.keys_pressed.add(event.key)
            elif event.type == pg.KEYUP:
                self.keys_down.discard(event.key)
                self.keys_released.add(event.key)
            elif event.type == pg.MOUSEBUTTONDOWN:
                self.mouse_down.add(event.button)
                self.mouse_pressed.add(event.button)
            elif event.type == pg.MOUSEBUTTONUP:
                self.mouse_down.discard(event.button)
                self.mouse_released.add(event.button)
        x, y = pg.mouse.get_pos()
        self.mouse_position = Vector2(float(x), float(y))

    def is_key_pressed(self, key: int) -> bool:
        return key in self.keys_down

    def is_key_just_pressed(self, key: int) -> bool:
        return key in self.keys_pressed

    def is_key_just_released(self, key: int) -> bool:
        return key in self.keys_released

    def is_action_pressed(self, name: str) -> bool:
        return any((key in self.keys_down for key in self.actions.get(name, ())))

    def is_action_just_pressed(self, name: str) -> bool:
        return any((key in self.keys_pressed for key in self.actions.get(name, ())))

    def is_action_just_released(self, name: str) -> bool:
        return any((key in self.keys_released for key in self.actions.get(name, ())))

    def action_pressed(self, name: str) -> bool:
        return self.is_action_pressed(name)

    def action_just_pressed(self, name: str) -> bool:
        return self.is_action_just_pressed(name)

    def action_just_released(self, name: str) -> bool:
        return self.is_action_just_released(name)

    def get_axis(self, negative: str, positive: str) -> float:
        return float(self.is_action_pressed(positive)) - float(self.is_action_pressed(negative))

    def get_vector(self, left: str, right: str, up: str, down: str) -> Vector2:
        v = Vector2(self.get_axis(left, right), self.get_axis(up, down))
        return v.normalized if v.length > 1.0 else v
