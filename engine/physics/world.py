from __future__ import annotations
from typing import List
from ..utils.vmath import Vector2, Vector3
from .body import BodyType, PhysicsBody2D
from .body3d import PhysicsBody3D
from .broadphase import SpatialBroadphase
from .query2d import QueryIndex2D, CombinedQueryIndex2D, segment_aabb, segment_circle
from ..scene.node import Node2D

class PhysicsWorld:
    def __init__(self, settings) -> None:
        self.settings = settings
        self._trigger_pairs_2d = {}
        self._trigger_pairs_3d = {}
        self._solid_pairs_2d = {}
        self._query_index_2d = None
        self._query_root_2d = None
        self._static_key_2d = None
        self._static_index_2d = None
        self.stats = {'bodies_2d':0,'bodies_3d':0,'candidate_pairs_2d':0,'candidate_pairs_3d':0}

    def _bodies(self, root) -> List[PhysicsBody2D]:
        return [n for n in root.walk() if isinstance(n, PhysicsBody2D) and n.collider.enabled and n.is_enabled_in_tree]

    def _bodies3d(self, root) -> List[PhysicsBody3D]:
        return [n for n in root.walk() if isinstance(n, PhysicsBody3D) and n.collider.enabled and n.is_enabled_in_tree]

    def step(self, root, delta: float) -> None:
        dt = delta * self.settings.time_scale
        if self.settings.time_scale <= 0:
            return
        bodies2d=[];bodies3d=[]
        for node in root.walk():
            if not node.is_enabled_in_tree:
                continue
            if isinstance(node,PhysicsBody2D) and node.collider.enabled:bodies2d.append(node)
            elif isinstance(node,PhysicsBody3D) and node.collider.enabled:bodies3d.append(node)
        self.stats.update(bodies_2d=len(bodies2d),bodies_3d=len(bodies3d),candidate_pairs_2d=0,candidate_pairs_3d=0)
        self._step2d(bodies2d, dt)
        self._step3d(bodies3d, dt)
        self.rebuild_queries_2d(root,bodies2d)

    def reset_contacts(self):
        self._trigger_pairs_2d.clear()
        self._trigger_pairs_3d.clear()
        self._solid_pairs_2d.clear()
        self._query_index_2d = None
        self._query_root_2d = None
        self._static_key_2d = None
        self._static_index_2d = None

    def _static_index(self,bodies):
        static=[b for b in bodies if b.body_type is BodyType.STATIC and not b.collider.is_trigger]
        transforms={}
        def transform(node):
            if node is None:return None
            if node.id not in transforms:
                parent=transform(node.parent)
                transforms[node.id]=(node.position.x,node.position.y,node.rotation,node.scale.x,node.scale.y,parent) if isinstance(node,Node2D) else parent
            return transforms[node.id]
        key=(self.settings.broadphase_cell_size_2d,tuple((b.id,transform(b),b.collider.size.x,b.collider.size.y,b.collider.offset.x,b.collider.offset.y,b.collider.shape) for b in static))
        if key!=self._static_key_2d:
            self._static_key_2d=key
            self._static_index_2d=QueryIndex2D(static,self.settings.broadphase_cell_size_2d)
        return self._static_index_2d

    def rebuild_queries_2d(self, root, bodies=None):
        bodies=self._bodies(root) if bodies is None else bodies
        self._query_root_2d = root
        static=self._static_index(bodies)
        dynamic=QueryIndex2D([b for b in bodies if b.body_type is not BodyType.STATIC or b.collider.is_trigger],self.settings.broadphase_cell_size_2d)
        self._query_index_2d = CombinedQueryIndex2D(static,dynamic)

    def _query2d(self, root, bounds, collision_mask, exclude, include_triggers):
        if self._query_index_2d is None or self._query_root_2d is not root:
            self.rebuild_queries_2d(root)
        excluded = set(exclude or ())
        for body in self._query_index_2d.query(bounds):
            if (body not in excluded and body.collider.enabled and body.is_enabled_in_tree and
                    body.collision_layer & collision_mask and (include_triggers or not body.collider.is_trigger)):
                yield body

    def raycast_2d_all(self, root, start, end, collision_mask=0xFFFFFFFF, exclude=None,
                       include_triggers=False, radius=0.0):
        r = max(0.0, float(radius))
        bounds = (min(start.x,end.x)-r, min(start.y,end.y)-r,
                  max(start.x,end.x)+r, max(start.y,end.y)+r)
        result = []
        for body in self._query2d(root, bounds, collision_mask, exclude, include_triggers):
            b = body.collider.bounds(body.global_position)
            fraction = segment_circle(start,end,b,r) if body.collider.shape=='circle' else segment_aabb(start, end, (b[0]-r,b[1]-r,b[2]+r,b[3]+r))
            if fraction is not None:
                result.append({'body':body, 'fraction':fraction, 'point':start+(end-start)*fraction,
                               'distance':(end-start).length*fraction})
        result.sort(key=lambda h: (h['fraction'], h['body'].id))
        return result

    def raycast_2d(self, root, start, end, **kwargs):
        hits = self.raycast_2d_all(root, start, end, **kwargs)
        return hits[0] if hits else None

    def overlap_circle_2d(self, root, center, radius, collision_mask=0xFFFFFFFF, exclude=None,
                          include_triggers=False):
        r = max(0.0, float(radius))
        found = []
        for body in self._query2d(root,(center.x-r,center.y-r,center.x+r,center.y+r),collision_mask,exclude,include_triggers):
            b=body.collider.bounds(body.global_position)
            if body.collider.shape=='circle':
                x=(b[0]+b[2])*.5;y=(b[1]+b[3])*.5;br=max(body.collider.size.x,body.collider.size.y)*.5
                if (x-center.x)**2+(y-center.y)**2 <= (r+br)**2:found.append(body)
                continue
            x=max(b[0],min(b[2],center.x)); y=max(b[1],min(b[3],center.y))
            if (x-center.x)**2+(y-center.y)**2 <= r*r:
                found.append(body)
        return found


    def raycast_3d(self, root, start: Vector3, end: Vector3, collision_mask: int=0xFFFFFFFF, exclude=None):
        exclude = set(exclude or ())
        direction = end - start
        length = direction.length
        if length <= 1e-12:
            return None
        best = None
        best_t = 2.0
        for body in self._bodies3d(root):
            if body in exclude or not (int(body.collision_layer) & int(collision_mask)):
                continue
            bounds = body.collider.bounds(body.global_position)
            hit = self._ray_aabb_segment(start, direction, bounds)
            if hit is None:
                continue
            t, normal = hit
            if 0.0 <= t <= 1.0 and t < best_t:
                best_t = t
                best = {
                    'body': body,
                    'point': start + direction * t,
                    'normal': normal,
                    'distance': length * t,
                    'fraction': t,
                }
        return best

    @staticmethod
    def _ray_aabb_segment(start: Vector3, direction: Vector3, bounds):
        mins = bounds[:3]
        maxs = bounds[3:]
        origins = (start.x, start.y, start.z)
        dirs = (direction.x, direction.y, direction.z)
        t_min = 0.0
        t_max = 1.0
        normal = Vector3()
        for axis in range(3):
            origin = origins[axis]
            delta = dirs[axis]
            lo = mins[axis]
            hi = maxs[axis]
            if abs(delta) <= 1e-12:
                if origin < lo or origin > hi:
                    return None
                continue
            inv = 1.0 / delta
            t1 = (lo - origin) * inv
            t2 = (hi - origin) * inv
            enter_normal_sign = -1.0 if delta > 0.0 else 1.0
            if t1 > t2:
                t1, t2 = t2, t1
            if t1 > t_min:
                t_min = t1
                normal = Vector3()
                if axis == 0:
                    normal.x = enter_normal_sign
                elif axis == 1:
                    normal.y = enter_normal_sign
                else:
                    normal.z = enter_normal_sign
            t_max = min(t_max, t2)
            if t_min > t_max:
                return None
        return t_min, normal

    def _step2d(self, bodies: list[PhysicsBody2D], dt: float) -> None:
        for body in bodies:
            body.on_ground = False
            if body.body_type is BodyType.STATIC:
                continue
            if body.body_type is BodyType.KINEMATIC:
                body.position = body.position + body.velocity * dt
                continue
            gravity = Vector2(0.0, self.settings.gravity * body.gravity_scale)
            body.velocity = body.velocity + (body.acceleration + gravity) * dt
            speed = body.velocity.length
            if speed > self.settings.max_velocity:
                body.velocity = body.velocity.normalized * self.settings.max_velocity
            body.position = body.position + body.velocity * dt
            body.acceleration = Vector2()
        current_triggers = {}
        entered_this_step = set()
        solids = {}


        collision_bodies=[b for b in bodies if b.collision_mask and b.collision_layer]
        static_index=self._static_index(collision_bodies)
        for _ in range(max(1, self.settings.iterations)):
            any_collision = False
            candidates=SpatialBroadphase(collision_bodies,2,getattr(self.settings,'broadphase_cell_size_2d',64),256,static_index).pairs()
            self.stats['candidate_pairs_2d'] += len(candidates)
            for i,j in candidates:
                a,b=collision_bodies[i],collision_bodies[j]
                if not (a.collider.enabled and b.collider.enabled and a.is_enabled_in_tree and b.is_enabled_in_tree):
                    continue
                trigger_pair = a.collider.is_trigger or b.collider.is_trigger
                if a.body_type is BodyType.STATIC and b.body_type is BodyType.STATIC and not trigger_pair:
                    continue
                if not (a.collision_mask & b.collision_layer and b.collision_mask & a.collision_layer):
                    continue
                if not a.collider.overlaps(a.global_position, b.collider, b.global_position):
                    continue
                if trigger_pair:
                    key = self._pair_key(a, b)
                    current_triggers[key] = (a, b)
                    if key not in self._trigger_pairs_2d and key not in entered_this_step:
                        entered_this_step.add(key)
                        a.signals.emit('body_entered', b)
                        b.signals.emit('body_entered', a)
                    continue
                solids[self._pair_key(a,b)] = (a,b)
                self._resolve2d(a, b)
                any_collision = True
            if not any_collision:
                break
        self._finish_trigger_pairs(self._trigger_pairs_2d, current_triggers)
        self._trigger_pairs_2d = current_triggers
        for key, (a,b) in solids.items():
            if key not in self._solid_pairs_2d:
                a.signals.emit('collision_entered', b); b.signals.emit('collision_entered', a)
            a.signals.emit('collision_stay', b); b.signals.emit('collision_stay', a)
        for key in self._solid_pairs_2d.keys() - solids.keys():
            a,b = self._solid_pairs_2d[key]
            a.signals.emit('collision_exited', b); b.signals.emit('collision_exited', a)
        self._solid_pairs_2d = solids

    def _step3d(self, bodies: list[PhysicsBody3D], dt: float) -> None:
        gravity_y = float(getattr(self.settings, 'gravity_3d', -9.81))
        for body in bodies:
            body.on_floor = False
            if body.body_type is BodyType.STATIC:
                continue
            if body.body_type is BodyType.KINEMATIC:
                body.position = body.position + body.velocity * dt
                continue
            gravity = Vector3(0.0, gravity_y * body.gravity_scale, 0.0)
            body.velocity = body.velocity + (body.acceleration + gravity) * dt
            speed = body.velocity.length
            if speed > self.settings.max_velocity:
                body.velocity = body.velocity.normalized * self.settings.max_velocity
            body.position = body.position + body.velocity * dt
            body.acceleration = Vector3()
        current_triggers = {}
        entered_this_step = set()
        for _ in range(max(1, self.settings.iterations)):
            any_collision = False
            candidates=SpatialBroadphase(bodies,3,getattr(self.settings,'broadphase_cell_size_3d',4)).pairs()
            self.stats['candidate_pairs_3d'] += len(candidates)
            for i,j in candidates:
                a,b=bodies[i],bodies[j]
                trigger_pair = a.collider.is_trigger or b.collider.is_trigger
                if a.body_type is BodyType.STATIC and b.body_type is BodyType.STATIC and not trigger_pair:
                    continue
                if not (a.collision_mask & b.collision_layer and b.collision_mask & a.collision_layer):
                    continue
                if not a.collider.overlaps(a.global_position, b.collider, b.global_position):
                    continue
                if trigger_pair:
                    key = self._pair_key(a, b)
                    current_triggers[key] = (a, b)
                    if key not in self._trigger_pairs_3d and key not in entered_this_step:
                        entered_this_step.add(key)
                        a.signals.emit('body_entered', b)
                        b.signals.emit('body_entered', a)
                    continue
                self._resolve3d(a, b)
                any_collision = True
            if not any_collision:
                break
        self._finish_trigger_pairs(self._trigger_pairs_3d, current_triggers)
        self._trigger_pairs_3d = current_triggers

    @staticmethod
    def _pair_key(a, b):
        return tuple(sorted((int(getattr(a, 'id', id(a))), int(getattr(b, 'id', id(b))))))

    @staticmethod
    def _finish_trigger_pairs(previous, current) -> None:
        for key in previous.keys() - current.keys():
            a, b = previous[key]
            a.signals.emit('body_exited', b)
            b.signals.emit('body_exited', a)

    @staticmethod
    def _resolve2d(a: PhysicsBody2D, b: PhysicsBody2D) -> None:
        ax1, ay1, ax2, ay2 = a.collider.bounds(a.global_position)
        bx1, by1, bx2, by2 = b.collider.bounds(b.global_position)
        overlap_x = min(ax2, bx2) - max(ax1, bx1)
        overlap_y = min(ay2, by2) - max(ay1, by1)
        if overlap_x <= 0 or overlap_y <= 0:
            return
        move_a = a.body_type is not BodyType.STATIC
        move_b = b.body_type is not BodyType.STATIC
        if not move_a and not move_b:
            return
        if overlap_x < overlap_y:
            direction = -1.0 if ax1 < bx1 else 1.0
            correction = Vector2(direction * overlap_x, 0.0)
            if move_a and move_b:
                a.position = a.position + correction * 0.5
                b.position = b.position - correction * 0.5
            elif move_a:
                a.position = a.position + correction
            else:
                b.position = b.position - correction
            if move_a:
                a.velocity.x = -a.velocity.x * a.restitution
            if move_b:
                b.velocity.x = -b.velocity.x * b.restitution
        else:
            direction = -1.0 if ay1 < by1 else 1.0
            correction = Vector2(0.0, direction * overlap_y)
            if move_a and move_b:
                a.position = a.position + correction * 0.5
                b.position = b.position - correction * 0.5
            elif move_a:
                a.position = a.position + correction
            else:
                b.position = b.position - correction
            if move_a:
                if direction < 0:
                    a.on_ground = True
                a.velocity.y = -a.velocity.y * a.restitution
            if move_b:
                if direction > 0:
                    b.on_ground = True
                b.velocity.y = -b.velocity.y * b.restitution

    @staticmethod
    def _resolve3d(a: PhysicsBody3D, b: PhysicsBody3D) -> None:
        ab = a.collider.bounds(a.global_position)
        bb = b.collider.bounds(b.global_position)
        overlaps = [min(ab[3+i], bb[3+i]) - max(ab[i], bb[i]) for i in range(3)]
        if any(v <= 0 for v in overlaps):
            return
        axis = min(range(3), key=lambda i: overlaps[i])
        move_a = a.body_type is not BodyType.STATIC
        move_b = b.body_type is not BodyType.STATIC
        if not move_a and not move_b:
            return
        ac = [(ab[i] + ab[i+3]) * 0.5 for i in range(3)]
        bc = [(bb[i] + bb[i+3]) * 0.5 for i in range(3)]
        direction = -1.0 if ac[axis] < bc[axis] else 1.0
        correction = Vector3()
        if axis == 0:
            correction.x = direction * overlaps[axis]
        elif axis == 1:
            correction.y = direction * overlaps[axis]
        else:
            correction.z = direction * overlaps[axis]
        if move_a and move_b:
            a.position = a.position + correction * 0.5
            b.position = b.position - correction * 0.5
        elif move_a:
            a.position = a.position + correction
        else:
            b.position = b.position - correction
        for body, sign in ((a, direction), (b, -direction)):
            if body.body_type is BodyType.STATIC:
                continue
            if axis == 0:
                body.velocity.x = -body.velocity.x * body.restitution
            elif axis == 1:
                if sign > 0:
                    body.on_floor = True
                body.velocity.y = -body.velocity.y * body.restitution
            else:
                body.velocity.z = -body.velocity.z * body.restitution
