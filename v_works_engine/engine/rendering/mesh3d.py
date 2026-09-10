from __future__ import annotations
import math
from dataclasses import dataclass, field
from ..utils.vmath import Vector3

@dataclass
class Mesh3D:
    vertices: list[Vector3] = field(default_factory=list)
    faces: list[tuple[int, ...]] = field(default_factory=list)

    @classmethod
    def cube(cls) -> 'Mesh3D':
        v = [
            Vector3(-0.5, -0.5, -0.5), Vector3(0.5, -0.5, -0.5),
            Vector3(0.5, 0.5, -0.5), Vector3(-0.5, 0.5, -0.5),
            Vector3(-0.5, -0.5, 0.5), Vector3(0.5, -0.5, 0.5),
            Vector3(0.5, 0.5, 0.5), Vector3(-0.5, 0.5, 0.5),
        ]
        f = [(0, 1, 2, 3), (5, 4, 7, 6), (4, 0, 3, 7), (1, 5, 6, 2), (3, 2, 6, 7), (4, 5, 1, 0)]
        return cls(v, f)

    @classmethod
    def plane(cls) -> 'Mesh3D':
        return cls([
            Vector3(-0.5, 0.0, -0.5), Vector3(0.5, 0.0, -0.5),
            Vector3(0.5, 0.0, 0.5), Vector3(-0.5, 0.0, 0.5),
        ], [(0, 1, 2, 3)])

    @classmethod
    def pyramid(cls) -> 'Mesh3D':
        return cls([
            Vector3(-0.5, -0.5, -0.5), Vector3(0.5, -0.5, -0.5),
            Vector3(0.5, -0.5, 0.5), Vector3(-0.5, -0.5, 0.5),
            Vector3(0.0, 0.5, 0.0),
        ], [(0, 1, 2, 3), (0, 4, 1), (1, 4, 2), (2, 4, 3), (3, 4, 0)])

    @classmethod
    def sphere(cls, segments: int=14, rings: int=9) -> 'Mesh3D':
        segments = max(6, int(segments))
        rings = max(4, int(rings))
        vertices: list[Vector3] = []
        faces: list[tuple[int, ...]] = []
        for r in range(rings + 1):
            phi = math.pi * r / rings
            y = math.cos(phi) * 0.5
            radius = math.sin(phi) * 0.5
            for s in range(segments):
                theta = 2.0 * math.pi * s / segments
                vertices.append(Vector3(math.cos(theta) * radius, y, math.sin(theta) * radius))
        for r in range(rings):
            row = r * segments
            next_row = (r + 1) * segments
            for s in range(segments):
                n = (s + 1) % segments
                faces.append((row + s, row + n, next_row + n, next_row + s))
        return cls(vertices, faces)

    @classmethod
    def cylinder(cls, segments: int=16) -> 'Mesh3D':
        segments = max(6, int(segments))
        vertices: list[Vector3] = []
        for y in (-0.5, 0.5):
            for s in range(segments):
                a = 2.0 * math.pi * s / segments
                vertices.append(Vector3(math.cos(a) * 0.5, y, math.sin(a) * 0.5))
        faces: list[tuple[int, ...]] = []
        faces.append(tuple(range(segments - 1, -1, -1)))
        faces.append(tuple(range(segments, segments * 2)))
        for s in range(segments):
            n = (s + 1) % segments
            faces.append((s, n, segments + n, segments + s))
        return cls(vertices, faces)


    @classmethod
    def from_obj(cls, path: str) -> 'Mesh3D':
        vertices: list[Vector3] = []
        faces: list[tuple[int, ...]] = []
        for raw in open(path, 'r', encoding='utf-8', errors='ignore'):
            line = raw.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split()
            if parts[0] == 'v' and len(parts) >= 4:
                vertices.append(Vector3(float(parts[1]), float(parts[2]), float(parts[3])))
            elif parts[0] == 'f' and len(parts) >= 4:
                idx = []
                for token in parts[1:]:
                    value = token.split('/')[0]
                    if not value:
                        continue
                    i = int(value)
                    i = len(vertices) + i if i < 0 else i - 1
                    if 0 <= i < len(vertices):
                        idx.append(i)
                if len(idx) >= 3:
                    faces.append(tuple(idx))
        if not vertices or not faces:
            raise ValueError(f'OBJ contains no usable mesh data: {path}')
        return cls(vertices, faces)


    @classmethod
    def from_stl(cls, path: str) -> 'Mesh3D':
        import struct
        raw = open(path, 'rb').read()
        vertices: list[Vector3] = []
        faces: list[tuple[int, ...]] = []
        is_binary = len(raw) >= 84
        if is_binary:
            count = struct.unpack_from('<I', raw, 80)[0]
            is_binary = 84 + count * 50 <= len(raw)
        if is_binary:
            count = struct.unpack_from('<I', raw, 80)[0]
            offset = 84
            for _ in range(count):
                if offset + 50 > len(raw):
                    break
                values = struct.unpack_from('<12fH', raw, offset)
                base = len(vertices)
                vertices.extend([
                    Vector3(values[3], values[4], values[5]),
                    Vector3(values[6], values[7], values[8]),
                    Vector3(values[9], values[10], values[11]),
                ])
                faces.append((base, base + 1, base + 2))
                offset += 50
        else:
            tri: list[Vector3] = []
            for line in raw.decode('utf-8', errors='ignore').splitlines():
                parts = line.strip().split()
                if len(parts) >= 4 and parts[0].lower() == 'vertex':
                    tri.append(Vector3(float(parts[1]), float(parts[2]), float(parts[3])))
                    if len(tri) == 3:
                        base = len(vertices)
                        vertices.extend(tri)
                        faces.append((base, base + 1, base + 2))
                        tri = []
        if not vertices or not faces:
            raise ValueError(f'STL contains no usable mesh data: {path}')
        return cls(vertices, faces)

    @classmethod
    def from_file(cls, path: str) -> 'Mesh3D':
        from pathlib import Path
        suffix = Path(path).suffix.lower()
        if suffix == '.stl':
            return cls.from_stl(path)
        return cls.from_obj(path)

    @classmethod
    def from_primitive(cls, name: str, segments: int=14, rings: int=9) -> 'Mesh3D':
        kind = str(name).lower()
        if kind == 'plane':
            return cls.plane()
        if kind == 'pyramid':
            return cls.pyramid()
        if kind == 'sphere':
            return cls.sphere(segments, rings)
        if kind == 'cylinder':
            return cls.cylinder(segments)
        return cls.cube()
