from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Tuple

@dataclass
class Vector2:
    x: float = 0.0
    y: float = 0.0

    def __add__(self, o: 'Vector2') -> 'Vector2':
        return Vector2(self.x + o.x, self.y + o.y)

    def __sub__(self, o: 'Vector2') -> 'Vector2':
        return Vector2(self.x - o.x, self.y - o.y)

    def __mul__(self, s):
        return Vector2(self.x * s.x, self.y * s.y) if isinstance(s, Vector2) else Vector2(self.x * s, self.y * s)
    __rmul__ = __mul__

    def __truediv__(self, s: float) -> 'Vector2':
        return Vector2(self.x / s, self.y / s)

    def __neg__(self) -> 'Vector2':
        return Vector2(-self.x, -self.y)

    def __repr__(self) -> str:
        return f'Vector2({self.x:.3f}, {self.y:.3f})'

    @property
    def length(self) -> float:
        return math.hypot(self.x, self.y)

    @property
    def normalized(self) -> 'Vector2':
        l = self.length
        return Vector2() if math.isclose(l, 0.0) else self / l

    def dot(self, o: 'Vector2') -> float:
        return self.x * o.x + self.y * o.y

    def cross(self, o: 'Vector2') -> float:
        return self.x * o.y - self.y * o.x

    @staticmethod
    def cross2(a: 'Vector2', b: 'Vector2') -> float:
        return a.cross(b)

    def distance_to(self, o: 'Vector2') -> float:
        return (self - o).length

    def lerp(self, o: 'Vector2', t: float) -> 'Vector2':
        return Vector2(self.x + (o.x - self.x) * t, self.y + (o.y - self.y) * t)

    def angle_to(self, o: 'Vector2') -> float:
        return math.atan2(o.y - self.y, o.x - self.x)

    def rotated(self, angle: float) -> 'Vector2':
        c, s = (math.cos(angle), math.sin(angle))
        return Vector2(self.x * c - self.y * s, self.x * s + self.y * c)

    def to_tuple(self) -> Tuple[float, float]:
        return (self.x, self.y)

@dataclass
class Vector3:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def __add__(self, o: 'Vector3') -> 'Vector3':
        return Vector3(self.x + o.x, self.y + o.y, self.z + o.z)

    def __sub__(self, o: 'Vector3') -> 'Vector3':
        return Vector3(self.x - o.x, self.y - o.y, self.z - o.z)

    def __mul__(self, s: float) -> 'Vector3':
        return Vector3(self.x * s, self.y * s, self.z * s)
    __rmul__ = __mul__

    def __truediv__(self, s: float) -> 'Vector3':
        return Vector3(self.x / s, self.y / s, self.z / s)

    def __neg__(self) -> 'Vector3':
        return Vector3(-self.x, -self.y, -self.z)

    def __repr__(self) -> str:
        return f'Vector3({self.x:.3f}, {self.y:.3f}, {self.z:.3f})'

    @property
    def length(self) -> float:
        return math.sqrt(self.x ** 2 + self.y ** 2 + self.z ** 2)

    @property
    def normalized(self) -> 'Vector3':
        l = self.length
        return Vector3() if math.isclose(l, 0.0) else self / l

    def dot(self, o: 'Vector3') -> float:
        return self.x * o.x + self.y * o.y + self.z * o.z

    def cross(self, o: 'Vector3') -> 'Vector3':
        return Vector3(self.y * o.z - self.z * o.y, self.z * o.x - self.x * o.z, self.x * o.y - self.y * o.x)

    def distance_to(self, o: 'Vector3') -> float:
        return (self - o).length

    def lerp(self, o: 'Vector3', t: float) -> 'Vector3':
        return Vector3(self.x + (o.x - self.x) * t, self.y + (o.y - self.y) * t, self.z + (o.z - self.z) * t)

    def to_tuple(self) -> Tuple[float, float, float]:
        return (self.x, self.y, self.z)

    @staticmethod
    def ZERO() -> 'Vector3':
        return Vector3()

    @staticmethod
    def UP() -> 'Vector3':
        return Vector3(0, 1, 0)

    @staticmethod
    def FORWARD() -> 'Vector3':
        return Vector3(0, 0, -1)

    @staticmethod
    def RIGHT() -> 'Vector3':
        return Vector3(1, 0, 0)


def rotate_euler(v: Vector3, rotation: Vector3) -> Vector3:
    cx, sx = math.cos(rotation.x), math.sin(rotation.x)
    cy, sy = math.cos(rotation.y), math.sin(rotation.y)
    cz, sz = math.cos(rotation.z), math.sin(rotation.z)
    x1 = v.x
    y1 = v.y * cx - v.z * sx
    z1 = v.y * sx + v.z * cx
    x2 = x1 * cy + z1 * sy
    y2 = y1
    z2 = -x1 * sy + z1 * cy
    return Vector3(x2 * cz - y2 * sz, x2 * sz + y2 * cz, z2)

def inverse_rotate_euler(v: Vector3, rotation: Vector3) -> Vector3:
    cz, sz = math.cos(-rotation.z), math.sin(-rotation.z)
    x1 = v.x * cz - v.y * sz
    y1 = v.x * sz + v.y * cz
    z1 = v.z
    cy, sy = math.cos(-rotation.y), math.sin(-rotation.y)
    x2 = x1 * cy + z1 * sy
    y2 = y1
    z2 = -x1 * sy + z1 * cy
    cx, sx = math.cos(-rotation.x), math.sin(-rotation.x)
    return Vector3(x2, y2 * cx - z2 * sx, y2 * sx + z2 * cx)

def direction_to_euler(direction: Vector3) -> Vector3:
    d = direction.normalized
    if not d.length:
        return Vector3()
    pitch = math.asin(max(-1.0, min(1.0, d.y)))
    yaw = math.atan2(-d.x, -d.z)
    return Vector3(pitch, yaw, 0.0)

@dataclass
class Quaternion:
    w: float = 1.0
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def __mul__(self, o: 'Quaternion') -> 'Quaternion':
        return Quaternion(self.w * o.w - self.x * o.x - self.y * o.y - self.z * o.z, self.w * o.x + self.x * o.w + self.y * o.z - self.z * o.y, self.w * o.y - self.x * o.z + self.y * o.w + self.z * o.x, self.w * o.z + self.x * o.y - self.y * o.x + self.z * o.w)

    @property
    def normalized(self) -> 'Quaternion':
        l = math.sqrt(self.w * self.w + self.x * self.x + self.y * self.y + self.z * self.z)
        return Quaternion() if math.isclose(l, 0.0) else Quaternion(self.w / l, self.x / l, self.y / l, self.z / l)

    def conjugate(self) -> 'Quaternion':
        return Quaternion(self.w, -self.x, -self.y, -self.z)

    def rotate_vector(self, v: Vector3) -> Vector3:
        q = self.normalized
        result = q * Quaternion(0, v.x, v.y, v.z) * q.conjugate()
        return Vector3(result.x, result.y, result.z)

    @staticmethod
    def from_axis_angle(axis: Vector3, angle: float) -> 'Quaternion':
        a = axis.normalized
        h = angle * 0.5
        s = math.sin(h)
        return Quaternion(math.cos(h), a.x * s, a.y * s, a.z * s)

@dataclass
class Transform2D:
    origin: Vector2 = field(default_factory=Vector2)
    rotation: float = 0.0
    scale: Vector2 = field(default_factory=lambda: Vector2(1, 1))

    def get_matrix(self):
        c, s = (math.cos(self.rotation), math.sin(self.rotation))
        return [[c * self.scale.x, -s * self.scale.y, self.origin.x], [s * self.scale.x, c * self.scale.y, self.origin.y], [0, 0, 1]]

    def transform_point(self, p: Vector2) -> Vector2:
        m = self.get_matrix()
        return Vector2(m[0][0] * p.x + m[0][1] * p.y + m[0][2], m[1][0] * p.x + m[1][1] * p.y + m[1][2])

    def inverse_transform_point(self, p: Vector2) -> Vector2:
        m = self.get_matrix()
        a, b, cx = m[0]
        d, e, cy = m[1]
        det = a * e - b * d
        if math.isclose(det, 0.0):
            return Vector2(p.x, p.y)
        return Vector2((e * p.x - b * p.y + b * cy - e * cx) / det, (-d * p.x + a * p.y + d * cx - a * cy) / det)

@dataclass
class Transform3D:
    origin: Vector3 = field(default_factory=Vector3)
    rotation: Quaternion = field(default_factory=Quaternion)
    scale: Vector3 = field(default_factory=lambda: Vector3(1, 1, 1))

    def transform_point(self, p: Vector3) -> Vector3:
        scaled = Vector3(p.x * self.scale.x, p.y * self.scale.y, p.z * self.scale.z)
        return self.rotation.rotate_vector(scaled) + self.origin
