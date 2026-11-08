from __future__ import annotations
from typing import Any, Callable, Optional
from ..scene.signals import SignalMap

class EventBus:

    def __init__(self) -> None:
        self._signals = SignalMap()

    def on(self, name: str, callback: Callable, user_data: Any=None) -> None:
        self._signals.connect(name, callback, user_data)

    def off(self, name: str, callback: Optional[Callable]=None) -> None:
        self._signals.disconnect(name, callback)

    def emit(self, name: str, *args: Any, **kwargs: Any) -> int:
        return self._signals.emit(name, *args, **kwargs)

    def clear(self) -> None:
        self._signals.clear()
