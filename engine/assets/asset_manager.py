from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict
from ..rendering.texture import Texture

class AssetManager:

    def __init__(self, renderer, audio_manager) -> None:
        self.renderer = renderer
        self.audio = audio_manager
        self._textures: Dict[str, Texture] = {}
        self._json: Dict[str, Any] = {}

    @staticmethod
    def _key(path: str) -> str:
        return str(Path(path).expanduser().resolve())

    def texture(self, path: str, alpha: bool=True) -> Texture:
        key = self._key(path)
        if key not in self._textures:
            self._textures[key] = Texture.load(self.renderer.pygame, key, alpha)
        return self._textures[key]

    def sound(self, path: str):
        return self.audio.load(self._key(path))

    def json(self, path: str) -> Any:
        key = self._key(path)
        if key not in self._json:
            with open(key, 'r', encoding='utf-8') as f:
                self._json[key] = json.load(f)
        return self._json[key]

    def clear(self) -> None:
        self._textures.clear()
        self._json.clear()
        self.audio.clear()
