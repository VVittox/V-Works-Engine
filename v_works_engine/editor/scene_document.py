from __future__ import annotations
from pathlib import Path
from typing import Optional
from engine.scene import Scene
from engine.scene.serialization import load_scene, save_scene

class SceneDocument:

    def __init__(self, scene: Optional[Scene]=None, path: Optional[str | Path]=None) -> None:
        self.scene = scene or Scene('Main')
        self.path = Path(path).resolve() if path else None
        self.dirty = False

    @property
    def display_name(self) -> str:
        return self.path.name if self.path else 'Untitled.vscene'

    def mark_dirty(self) -> None:
        self.dirty = True

    def save(self, path: Optional[str | Path]=None) -> Path:
        if path is not None:
            self.path = Path(path).resolve()
        if self.path is None:
            raise ValueError('Scene has no path')
        save_scene(self.scene, self.path)
        self.dirty = False
        return self.path

    @classmethod
    def load(cls, path: str | Path) -> 'SceneDocument':
        path = Path(path).resolve()
        return cls(load_scene(path), path)
