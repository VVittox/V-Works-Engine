from __future__ import annotations
from pathlib import Path

class Texture:

    def __init__(self, surface, path: str='') -> None:
        self.surface = surface
        self.path = path

    @property
    def width(self) -> int:
        return self.surface.get_width()

    @property
    def height(self) -> int:
        return self.surface.get_height()

    @classmethod
    def load(cls, pygame_module, path: str, alpha: bool=True) -> 'Texture':
        p = Path(path)
        surface = pygame_module.image.load(str(p))
        surface = surface.convert_alpha() if alpha else surface.convert()
        return cls(surface, str(p))
