from __future__ import annotations
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

@dataclass
class VResource:
    resource_type: str = 'Resource'
    data: dict[str, Any] = field(default_factory=dict)
    path: str = ''

    def to_dict(self) -> dict[str, Any]:
        return {'format': 'vworks_resource', 'version': 1, 'type': self.resource_type, 'data': self.data}

    def save(self, path: str | Path | None=None) -> Path:
        target = Path(path or self.path).expanduser().resolve()
        if not str(target):
            raise ValueError('Resource has no path')
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding='utf-8')
        self.path = str(target)
        return target

    @classmethod
    def load(cls, path: str | Path) -> 'VResource':
        target = Path(path).expanduser().resolve()
        payload = json.loads(target.read_text(encoding='utf-8'))
        if payload.get('format') != 'vworks_resource':
            raise ValueError(f'Not a V Works resource: {target}')
        return cls(str(payload.get('type', 'Resource')), dict(payload.get('data', {})), str(target))

@dataclass
class Material2D(VResource):
    resource_type: str = 'Material2D'

    @classmethod
    def default(cls) -> 'Material2D':
        return cls(data={'tint': [255, 255, 255, 255], 'blend_mode': 'alpha', 'shader': '', 'shader_preset': 'none', 'params': {'pixel_size': 4, 'outline_size': 2}})

@dataclass
class Shader2D(VResource):
    resource_type: str = 'Shader2D'

    @classmethod
    def default(cls) -> 'Shader2D':
        return cls(data={'preset': 'none', 'code': '// VSL 0.1 - CPU shader metadata\n// presets: none, grayscale, invert, pixelate, tint\n', 'params': {}})

@dataclass
class TileSetResource(VResource):
    resource_type: str = 'TileSet2D'

    @classmethod
    def default(cls) -> 'TileSetResource':
        return cls(data={'texture': '', 'tile_width': 32, 'tile_height': 32, 'columns': 8, 'margin': 0, 'spacing': 0})

class ResourceManager:

    def __init__(self, project_root: str | Path) -> None:
        self.project_root = Path(project_root).resolve()
        self._cache: dict[str, VResource] = {}

    def resolve(self, path: str | Path) -> Path:
        p = Path(path)
        return p.resolve() if p.is_absolute() else (self.project_root / p).resolve()

    def load(self, path: str | Path, refresh: bool=False) -> VResource:
        target = self.resolve(path)
        key = str(target)
        if refresh or key not in self._cache:
            self._cache[key] = VResource.load(target)
        return self._cache[key]

    def data(self, path: str | Path, default: dict[str, Any] | None=None) -> dict[str, Any]:
        if not path:
            return dict(default or {})
        try:
            return dict(self.load(path).data)
        except (FileNotFoundError, ValueError, json.JSONDecodeError):
            return dict(default or {})

    def clear(self) -> None:
        self._cache.clear()
