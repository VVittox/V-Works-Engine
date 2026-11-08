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
        self.poll_mouse = True
        self.quit_requested = False
        self.actions: Dict[str, Set[int]] = defaultdict(set)
        self.pad_axes = {}
        self.pad_buttons = set()
        self.pad_pressed = set()
        self.pad_released = set()
        self.touches = {}
        self.pointer_pressed = []
        self.pointer_released = []
        self.focus_lost = False
        self.mouse_wheel = 0
        self._joysticks = {}
        if hasattr(self.pg, 'joystick'):
            self.pg.joystick.init()
            for index in range(self.pg.joystick.get_count()):
                joystick = self.pg.joystick.Joystick(index)
                joystick.init()
                self._joysticks[joystick.get_instance_id()] = joystick
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
        self.pad_pressed.clear()
        self.pad_released.clear()
        self.pointer_pressed.clear()
        self.pointer_released.clear()
        self.focus_lost = False
        self.mouse_wheel = 0
        event_position = None
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
                if getattr(event, 'touch', False):
                    continue
                self.mouse_down.add(event.button)
                self.mouse_pressed.add(event.button)
                if event.button == 1:
                    self.pointer_pressed.append(('mouse', Vector2(*event.pos)))
                if hasattr(event, 'pos'): event_position = event.pos
            elif event.type == pg.MOUSEBUTTONUP:
                if getattr(event, 'touch', False):
                    continue
                self.mouse_down.discard(event.button)
                self.mouse_released.add(event.button)
                if event.button == 1:
                    self.pointer_released.append(('mouse', Vector2(*event.pos)))
                if hasattr(event, 'pos'): event_position = event.pos
            elif event.type == getattr(pg, 'MOUSEMOTION', -10):
                event_position = event.pos
            elif event.type == getattr(pg, 'MOUSEWHEEL', -11):
                self.mouse_wheel += event.y
            elif event.type == getattr(pg, 'JOYDEVICEADDED', -12):
                joystick = pg.joystick.Joystick(event.device_index)
                joystick.init()
                self._joysticks[joystick.get_instance_id()] = joystick
            elif event.type == getattr(pg, 'JOYDEVICEREMOVED', -13):
                self._joysticks.pop(event.instance_id, None)
                self.pad_axes.clear(); self.pad_buttons.clear()
            elif event.type == getattr(pg, 'JOYAXISMOTION', -14):
                self.pad_axes[event.axis] = float(event.value)
            elif event.type == getattr(pg, 'JOYBUTTONDOWN', -15):
                self.pad_buttons.add(event.button); self.pad_pressed.add(event.button)
            elif event.type == getattr(pg, 'JOYBUTTONUP', -16):
                self.pad_buttons.discard(event.button); self.pad_released.add(event.button)
            elif event.type in (getattr(pg,'FINGERDOWN',-17),getattr(pg,'FINGERMOTION',-18),getattr(pg,'FINGERUP',-19)):
                surface = pg.display.get_surface()
                w,h = surface.get_size() if surface is not None else (1,1)
                position = Vector2(event.x*w,event.y*h)
                if event.type == pg.FINGERDOWN:
                    self.pointer_pressed.append((event.finger_id, position))
                    self.touches[event.finger_id] = position
                elif event.type == pg.FINGERUP:
                    self.pointer_released.append((event.finger_id, position))
                    self.touches.pop(event.finger_id,None)
                else:
                    self.touches[event.finger_id] = position
            elif event.type in (getattr(pg,'WINDOWFOCUSLOST',-20),getattr(pg,'APP_WILLENTERBACKGROUND',-21)):
                self.focus_lost = True
                self.keys_down.clear(); self.mouse_down.clear(); self.touches.clear()
                self.pad_axes.clear(); self.pad_buttons.clear()
        if event_position is not None:
            self.mouse_position=Vector2(*event_position)
        elif self.poll_mouse:
            self.mouse_position=Vector2(*pg.mouse.get_pos())

    def get_gamepad_vector(self, dead_zone=0.12) -> Vector2:
        vector = Vector2(self.pad_axes.get(0,0), self.pad_axes.get(1,0))
        if vector.length < dead_zone:
            return Vector2()
        return vector.normalized if vector.length > 1 else vector

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
