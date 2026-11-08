from __future__ import annotations
import time
from collections import deque
from contextlib import contextmanager

class Profiler:

    def __init__(self, history: int=180) -> None:
        self.history = max(10, int(history))
        self.samples: dict[str, deque[float]] = {}
        self.frame_ms = 0.0
        self.physics_ms = 0.0
        self.process_ms = 0.0
        self.draw_ms = 0.0

    def push(self, name: str, milliseconds: float) -> None:
        bucket = self.samples.setdefault(name, deque(maxlen=self.history))
        bucket.append(float(milliseconds))
        setattr(self, f'{name}_ms', float(milliseconds)) if hasattr(self, f'{name}_ms') else None

    def avg(self, name: str) -> float:
        bucket = self.samples.get(name)
        return sum(bucket) / len(bucket) if bucket else 0.0

    def max(self, name: str) -> float:
        bucket = self.samples.get(name)
        return max(bucket) if bucket else 0.0

    @contextmanager
    def measure(self, name: str):
        t0 = time.perf_counter()
        try:
            yield
        finally:
            self.push(name, (time.perf_counter() - t0) * 1000.0)

    def snapshot(self) -> dict[str, float]:
        return {name: self.avg(name) for name in sorted(self.samples)}
