
from __future__ import annotations
import math
from .node import Node3D
from ..utils.vmath import Vector3


class Path3D(Node3D):


    def __init__(self, name='Path3D'):
        super().__init__(name)
        self.points = [Vector3(0, 0, 0), Vector3(0, 0, -5)]
        self.closed = False

    def _segments(self):
        if len(self.points) < 2:
            return []
        pairs = list(zip(self.points, self.points[1:]))
        if self.closed and len(self.points) > 2:
            pairs.append((self.points[-1], self.points[0]))
        return pairs

    @property
    def length(self):
        return sum((b-a).length for a,b in self._segments())

    def sample(self, distance: float, *, wrap=False) -> Vector3:

        if not self.points:
            return Vector3()
        segments = self._segments()
        total = self.length
        if not segments or total <= 1e-12:
            return self.points[0]
        remaining = float(distance) % total if wrap else max(0.0, min(float(distance), total))
        for a, b in segments:
            width = (b-a).length
            if remaining <= width or (a,b) == segments[-1]:
                return a.lerp(b, remaining / width if width > 1e-12 else 0.0)
            remaining -= width
        return segments[-1][1]


class PathFollow3D(Node3D):


    def __init__(self, name='PathFollow3D'):
        super().__init__(name)
        self.path_node = '..'
        self.progress = 0.0
        self.speed = 0.0
        self.loop = True

    def _process(self, delta: float):
        path = self.get_node(self.path_node)
        if not isinstance(path, Path3D):
            return
        if self.speed:
            self.progress += float(self.speed) * max(0.0, float(delta))
        point = path.to_global(path.sample(self.progress,wrap=self.loop))
        if isinstance(self.parent, Node3D):
            self.position = self.parent.to_local(point)
        else:
            self.position = point


class LookAt3D(Node3D):


    def __init__(self, name='LookAt3D'):
        super().__init__(name)
        self.target_path = ''
        self.tracking = True

    def _process(self, delta: float):
        if not self.tracking or not self.target_path:
            return
        target = self.get_node(self.target_path)
        if isinstance(target, Node3D) and target is not self:
            self.look_at(target.global_position)
