from __future__ import annotations
from typing import Callable

class FixedTimestepLoop:

    def __init__(self, physics_fps: int=60, max_frame_delta: float=0.25) -> None:
        self.physics_fps = max(1, physics_fps)
        self.fixed_delta = 1.0 / self.physics_fps
        self.max_frame_delta = max_frame_delta
        self.accumulator = 0.0

    def reset(self) -> None:
        self.accumulator = 0.0

    def advance(self, frame_delta: float, physics_callback: Callable[[float], None], process_callback: Callable[[float], None]) -> float:
        frame_delta = min(max(frame_delta, 0.0), self.max_frame_delta)
        self.accumulator += frame_delta
        while self.accumulator >= self.fixed_delta:
            physics_callback(self.fixed_delta)
            self.accumulator -= self.fixed_delta
        process_callback(frame_delta)
        return self.accumulator / self.fixed_delta
