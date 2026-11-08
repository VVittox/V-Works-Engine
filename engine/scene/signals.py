from __future__ import annotations
import inspect
import weakref
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

def _same_callable(a: Callable, b: Callable) -> bool:
    if inspect.ismethod(a) and inspect.ismethod(b):
        return a.__self__ is b.__self__ and a.__func__ is b.__func__
    return a is b

@dataclass
class _Listener:
    user_data: Any = None
    strong: Optional[Callable] = None
    weak: Optional[weakref.WeakMethod] = None

    @classmethod
    def from_callable(cls, func: Callable, user_data: Any=None) -> '_Listener':
        if inspect.ismethod(func) and func.__self__ is not None:
            return cls(user_data=user_data, weak=weakref.WeakMethod(func))
        return cls(user_data=user_data, strong=func)

    def get(self) -> Optional[Callable]:
        if self.strong is not None:
            return self.strong
        return self.weak() if self.weak is not None else None

class Signal:

    def __init__(self, name: str) -> None:
        self.name = name
        self._listeners: List[_Listener] = []

    def connect(self, func: Callable, user_data: Any=None) -> None:
        if not callable(func):
            raise TypeError('Signal callback must be callable')
        for listener in self._listeners:
            current = listener.get()
            if current is not None and _same_callable(current, func):
                return
        self._listeners.append(_Listener.from_callable(func, user_data))

    def disconnect(self, func: Optional[Callable]=None) -> None:
        if func is None:
            self._listeners.clear()
            return
        kept: List[_Listener] = []
        for listener in self._listeners:
            current = listener.get()
            if current is None or _same_callable(current, func):
                continue
            kept.append(listener)
        self._listeners = kept

    def emit(self, *args: Any, **kwargs: Any) -> int:
        called = 0
        dead: List[_Listener] = []
        for listener in list(self._listeners):
            func = listener.get()
            if func is None:
                dead.append(listener)
                continue
            try:
                if listener.user_data is not None:
                    func(listener.user_data, *args, **kwargs)
                else:
                    func(*args, **kwargs)
                called += 1
            except Exception as exc:
                print(f'[Signal:{self.name}] handler error: {exc}')
        if dead:
            self._listeners = [x for x in self._listeners if x not in dead]
        return called

    def connected_count(self) -> int:
        return sum((1 for listener in self._listeners if listener.get() is not None))

    @property
    def connected(self) -> bool:
        return self.connected_count() > 0

class SignalMap:

    def __init__(self) -> None:
        self._signals: Dict[str, Signal] = {}

    def add(self, *names: str) -> 'SignalMap':
        for name in names:
            self._signals.setdefault(name, Signal(name))
        return self

    def get(self, name: str) -> Signal:
        self._signals.setdefault(name, Signal(name))
        return self._signals[name]

    def emit(self, name: str, *args: Any, **kwargs: Any) -> int:
        signal = self._signals.get(name)
        return signal.emit(*args, **kwargs) if signal is not None else 0

    def connect(self, name: str, func: Callable, user_data: Any=None) -> None:
        self.get(name).connect(func, user_data)

    def disconnect(self, name: str, func: Optional[Callable]=None) -> None:
        signal = self._signals.get(name)
        if signal is not None:
            signal.disconnect(func)

    def clear(self) -> None:
        for signal in self._signals.values():
            signal.disconnect()
        self._signals.clear()

    @property
    def names(self) -> List[str]:
        return list(self._signals.keys())

    def __contains__(self, name: str) -> bool:
        return name in self._signals
