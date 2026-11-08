from __future__ import annotations
from typing import Optional, Tuple
from .node import Node

class Scene(Node):

    def __init__(self, name: str='Scene', background_color: Optional[Tuple[int, int, int]]=None) -> None:
        super().__init__(name)
        self.background_color = background_color
        self.inherited_from: str = ''
