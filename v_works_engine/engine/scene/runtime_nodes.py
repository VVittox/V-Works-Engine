from __future__ import annotations
from pathlib import Path
from .node import Node, Node2D

class Timer(Node):

    def __init__(self, name: str='Timer') -> None:
        super().__init__(name)
        self.wait_time = 1.0
        self.one_shot = False
        self.autostart = False
        self.paused = False
        self.time_left = 0.0
        self.running = False
        self.signals.add('timeout')

    def _ready(self) -> None:
        if self.autostart:
            self.start()

    def start(self, wait_time: float | None=None) -> None:
        if wait_time is not None:
            self.wait_time = max(0.0001, float(wait_time))
        self.time_left = max(0.0001, float(self.wait_time))
        self.running = True

    def stop(self) -> None:
        self.running = False
        self.time_left = 0.0

    def _process(self, delta: float) -> None:
        if not self.running or self.paused:
            return
        self.time_left -= delta
        if self.time_left <= 0:
            self.signals.emit('timeout')
            if self.one_shot:
                self.stop()
            else:
                self.time_left += max(0.0001, self.wait_time)

class AudioStreamPlayer2D(Node2D):

    def __init__(self, name: str='AudioStreamPlayer2D') -> None:
        super().__init__(name)
        self.stream_path = ''
        self.autoplay = False
        self.loop = False
        self.volume = 1.0
        self._channel = None

    def _ready(self) -> None:
        if self.autoplay:
            self.play()

    def play(self) -> None:
        tree = self.get_tree()
        engine = tree.engine if tree else None
        if engine is None or engine.audio is None or (not self.stream_path):
            return
        path = engine.project_root / self.stream_path if not Path(self.stream_path).is_absolute() else Path(self.stream_path)
        self._channel = engine.audio.play(str(path), loops=-1 if self.loop else 0, volume=self.volume)

    def stop(self) -> None:
        if self._channel is not None:
            try:
                self._channel.stop()
            except Exception:
                pass
        self._channel = None

class Button2D(Node2D):

    def __init__(self, name: str='Button2D', text: str='Button') -> None:
        super().__init__(name)
        from ..utils.vmath import Vector2
        self.text = text
        self.size = Vector2(160, 44)
        self.color = (55, 65, 82)
        self.hover_color = (72, 90, 116)
        self.text_color = (245, 245, 248)
        self.disabled = False
        self.screen_space = True
        self._hovered = False
        self.signals.add('pressed')

    def _process(self, delta: float) -> None:
        tree = self.get_tree()
        engine = tree.engine if tree else None
        if engine is None or engine.input is None or engine.renderer is None or self.disabled:
            return
        mouse = engine.input.mouse_position
        if self.screen_space:
            p = self.global_position
        else:
            p = engine.renderer.camera.world_to_screen(self.global_position, engine.renderer.size)
        gs = self.global_scale
        w = self.size.x * abs(gs.x)
        h = self.size.y * abs(gs.y)
        self._hovered = p.x <= mouse.x <= p.x + w and p.y <= mouse.y <= p.y + h
        if self._hovered and 1 in engine.input.mouse_pressed:
            self.signals.emit('pressed')

    def _draw(self, renderer) -> None:
        if not self.visible:
            return
        from ..utils.vmath import Vector2
        color = self.hover_color if self._hovered and (not self.disabled) else self.color
        renderer.draw_rect(self.global_position, self.size * self.global_scale, color, world=not self.screen_space)
        renderer.draw_text(self.text, self.global_position + Vector2(12, 10), 18, self.text_color, world=not self.screen_space)
