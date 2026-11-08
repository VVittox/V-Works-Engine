
from __future__ import annotations
import math
from engine.scene.node import Node3D
from engine.utils.vmath import Vector3

AXES = {'X':Vector3(1,0,0),'Y':Vector3(0,1,0),'Z':Vector3(0,0,1)}

def copy_vector(v):
    return Vector3(v.x,v.y,v.z)

def axes_for(node,local=False):
    if local:
        return {'X':node.global_right,'Y':node.global_up,'Z':-node.global_forward}
    return {key:copy_vector(v) for key,v in AXES.items()}

def plane_hit(ray,origin,normal):
    start,direction=ray;denom=direction.dot(normal)
    if abs(denom)<1e-8:return None
    distance=(origin-start).dot(normal)/denom
    return start+direction*distance if distance>=0 else None

def set_world_position(node,position):
    parent=node.parent
    while parent is not None and not isinstance(parent,Node3D):parent=parent.parent
    node.position=parent.to_local(position) if parent is not None else copy_vector(position)

def triangle_hit(ray,a,b,c):
    origin,direction=ray;edge1=b-a;edge2=c-a;p=direction.cross(edge2);det=edge1.dot(p)
    if abs(det)<1e-10:return None
    inverse=1/det;s=origin-a;u=s.dot(p)*inverse
    if not 0<=u<=1:return None
    q=s.cross(edge1);v=direction.dot(q)*inverse
    if v<0 or u+v>1:return None
    distance=edge2.dot(q)*inverse
    return distance if distance>=0 else None

class TransformDrag:
    def __init__(self,node,view,mouse,mode='move',constraint='VIEW',local=False):
        self.node=node;self.view=view;self.mouse=mouse;self.mode=mode;self.local=local
        self.position=copy_vector(node.position);self.rotation=copy_vector(node.rotation);self.scale=copy_vector(node.scale)
        self.origin=copy_vector(node.global_position);self.axes=axes_for(node,local if mode=='move' else True)
        self.set_constraint(constraint)

    def set_constraint(self,constraint):
        self.constraint=constraint
        if constraint in AXES:
            axis=self.axes[constraint]
            normal=self.view.forward-axis*self.view.forward.dot(axis)
            if normal.length<1e-6:normal=self.view.up-axis*self.view.up.dot(axis)
            self.normal=normal.normalized;self.active=[axis]
        elif constraint in ('XY','XZ','YZ'):
            self.active=[self.axes[key] for key in constraint]
            self.normal=self.active[0].cross(self.active[1]).normalized
        else:
            self.normal=self.view.forward;self.active=[self.view.right,self.view.up]
        self.anchor=plane_hit(self.view.ray(*self.mouse),self.origin,self.normal)

    def update(self,mouse,snap=0.,precision=False):
        factor=.1 if precision else 1.
        dx=(mouse[0]-self.mouse[0])*factor;dy=(mouse[1]-self.mouse[1])*factor
        if self.mode=='move':
            if self.constraint in AXES:
                axis=self.axes[self.constraint];a=self.view.project(self.origin)
                b=self.view.project(self.origin+axis*self.view.units_per_pixel(self.origin)*100)
                if a is not None and b is not None and math.hypot(a[0]-b[0],a[1]-b[1])<8:


                    value=-dy*self.view.units_per_pixel(self.origin)
                    if snap:value=round(value/snap)*snap
                    set_world_position(self.node,self.origin+axis*value)
                    return self.changed
            hit=plane_hit(self.view.ray(*mouse),self.origin,self.normal)
            if hit is None or self.anchor is None:return False
            delta=(hit-self.anchor)*factor
            if self.constraint in AXES or self.constraint in ('XY','XZ','YZ'):
                values=[delta.dot(axis) for axis in self.active]
                if len(self.active)==2:
                    dot=self.active[0].dot(self.active[1]);denom=1-dot*dot
                    if abs(denom)<1e-9:return False
                    values=[(values[0]-dot*values[1])/denom,(values[1]-dot*values[0])/denom]
                if snap:values=[round(value/snap)*snap for value in values]
                delta=Vector3()
                for axis,value in zip(self.active,values):delta=delta+axis*value
            elif snap:
                delta=self.view.right*(round(delta.dot(self.view.right)/snap)*snap)+self.view.up*(round(delta.dot(self.view.up)/snap)*snap)
            set_world_position(self.node,self.origin+delta)
        elif self.mode=='rotate':
            angle=(dx-dy)*.01
            if snap:angle=round(angle/math.radians(15))*math.radians(15)
            self.node.rotation=copy_vector(self.rotation)
            key=self.constraint if self.constraint in AXES else 'Y'
            setattr(self.node.rotation,key.lower(),getattr(self.rotation,key.lower())+angle)
        else:
            factor=max(.001,1+(dx-dy)*.01)
            value=copy_vector(self.scale)
            for key in self.constraint if self.constraint in AXES else 'XYZ':
                component=getattr(self.scale,key.lower())*factor
                if snap:component=round(component/max(.05,snap))*max(.05,snap)

                setattr(value,key.lower(),max(.001,abs(component))*(-1 if getattr(self.scale,key.lower())<0 else 1))
            self.node.scale=value
        return self.changed

    @property
    def changed(self):
        return any((getattr(self.node,key)-value).length>1e-9 for key,value in
                   (('position',self.position),('rotation',self.rotation),('scale',self.scale)))

    def cancel(self):
        self.node.position=copy_vector(self.position);self.node.rotation=copy_vector(self.rotation);self.node.scale=copy_vector(self.scale)
