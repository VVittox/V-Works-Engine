
from __future__ import annotations
import itertools
import math


class QueryIndex2D:
    def __init__(self, bodies, cell_size=64, max_cells=256):
        self.cell_size = max(1.0, float(cell_size))
        self.bodies = list(bodies)
        self.cells = {}
        self.large = []
        for body in self.bodies:
            spans = self._spans(body.collider.bounds(body.global_position))
            if len(spans[0]) * len(spans[1]) > max_cells:
                self.large.append(body)
            else:
                for cell in itertools.product(*spans):
                    self.cells.setdefault(cell, []).append(body)

    def _spans(self, bounds):
        s = self.cell_size
        return [range(math.floor(bounds[i]/s), math.floor(bounds[i+2]/s)+1) for i in (0, 1)]

    def query(self, bounds):
        spans = self._spans(bounds)
        if len(spans[0]) * len(spans[1]) > 4096:
            return self.bodies
        found = {body.id: body for body in self.large}
        for cell in itertools.product(*spans):
            for body in self.cells.get(cell, ()):
                found[body.id] = body
        return list(found.values())

class CombinedQueryIndex2D:
    def __init__(self,static,dynamic):
        self.static=static;self.dynamic=dynamic
    def query(self,bounds):
        return self.static.query(bounds)+self.dynamic.query(bounds)


def segment_aabb(start, end, bounds):
    lo, hi = 0.0, 1.0
    for origin, delta, minimum, maximum in (
        (start.x, end.x-start.x, bounds[0], bounds[2]),
        (start.y, end.y-start.y, bounds[1], bounds[3]),
    ):
        if abs(delta) < 1e-12:
            if not minimum <= origin <= maximum:
                return None
        else:
            a, b = (minimum-origin)/delta, (maximum-origin)/delta
            lo = max(lo, min(a, b)); hi = min(hi, max(a, b))
            if lo > hi:
                return None
    return lo

def segment_circle(start,end,bounds,radius=0.0):
    cx=(bounds[0]+bounds[2])*.5;cy=(bounds[1]+bounds[3])*.5
    r=max(bounds[2]-bounds[0],bounds[3]-bounds[1])*.5+radius
    x,y=start.x-cx,start.y-cy;dx,dy=end.x-start.x,end.y-start.y
    c=x*x+y*y-r*r
    if c<=0:return 0.0
    a=dx*dx+dy*dy
    if a<1e-12:return None
    b=2*(x*dx+y*dy);disc=b*b-4*a*c
    if disc<0:return None
    t=(-b-math.sqrt(disc))/(2*a)
    return t if 0<=t<=1 else None
