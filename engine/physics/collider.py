from __future__ import annotations
from dataclasses import dataclass, field
from typing import Tuple
from ..utils.vmath import Vector2

@dataclass
class AABBCollider:
    size: Vector2 = field(default_factory=lambda: Vector2(32, 32))
    offset: Vector2 = field(default_factory=Vector2)
    enabled: bool = True
    is_trigger: bool = False
    shape: str = 'box'

    def bounds(self, position: Vector2) -> Tuple[float, float, float, float]:
        x = position.x + self.offset.x
        y = position.y + self.offset.y
        return (x, y, x + self.size.x, y + self.size.y)

    def overlaps(self, position: Vector2, other: 'AABBCollider', other_position: Vector2) -> bool:
        a = self.bounds(position)
        b = other.bounds(other_position)
        if self.shape == 'circle' or other.shape == 'circle':
            if self.shape == 'circle' and other.shape == 'circle':
                ac=((a[0]+a[2])*.5,(a[1]+a[3])*.5);bc=((b[0]+b[2])*.5,(b[1]+b[3])*.5)
                radius=(max(self.size.x,self.size.y)+max(other.size.x,other.size.y))*.5
                return (ac[0]-bc[0])**2+(ac[1]-bc[1])**2<radius*radius
            circle,box,collider=(a,b,self) if self.shape=='circle' else (b,a,other)
            x=(circle[0]+circle[2])*.5;y=(circle[1]+circle[3])*.5;r=max(collider.size.x,collider.size.y)*.5
            px=max(box[0],min(box[2],x));py=max(box[1],min(box[3],y))
            return (x-px)**2+(y-py)**2<r*r
        return a[0] < b[2] and a[2] > b[0] and (a[1] < b[3]) and (a[3] > b[1])
