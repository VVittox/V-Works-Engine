
from __future__ import annotations
import itertools,math
from .body import BodyType

class SpatialBroadphase:
    def __init__(self,bodies,dimensions,cell_size=4.,max_cells=256,static_index=None):
        self.bodies=bodies;self.dimensions=dimensions
        self.cell_size=max(.001,float(cell_size));self.max_cells=max_cells
        self.cells={};self.large=[];self.ranges=[]
        self.static_index=static_index if dimensions==2 else None
        self.body_indices={body.id:i for i,body in enumerate(bodies)} if self.static_index is not None else {}
        static_ids={body.id for body in self.static_index.bodies} if self.static_index is not None else set()
        self.active=[i for i,b in enumerate(bodies) if b.body_type is not BodyType.STATIC or b.collider.is_trigger]
        if not self.active:return
        for i,body in enumerate(bodies):
            if body.id in static_ids:
                self.ranges.append(None)
                continue
            bounds=body.collider.bounds(body.global_position)
            spans=[range(math.floor(bounds[a]/self.cell_size),math.floor(bounds[a+dimensions]/self.cell_size)+1) for a in range(dimensions)]
            self.ranges.append(spans)
            if math.prod(len(r) for r in spans)>max_cells:
                self.large.append(i);continue
            for cell in itertools.product(*spans):self.cells.setdefault(cell,[]).append(i)

    def pairs(self):
        pairs=set();all_indices=range(len(self.bodies))
        for i in self.active:
            spans=self.ranges[i]
            candidates=set(self.large)
            if self.static_index is not None:
                candidates.update(self.body_indices[b.id] for b in self.static_index.large if b.id in self.body_indices)
            if math.prod(len(r) for r in spans)>self.max_cells:
                candidates.update(all_indices)
            else:
                for cell in itertools.product(*spans):
                    candidates.update(self.cells.get(cell,()))
                    if self.static_index is not None:
                        candidates.update(self.body_indices[b.id] for b in self.static_index.cells.get(cell,()) if b.id in self.body_indices)
            for j in candidates:
                if i==j:continue
                pairs.add((min(i,j),max(i,j)))

        return sorted(pairs)
