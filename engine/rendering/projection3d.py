
from __future__ import annotations
import math
from ..utils.vmath import Vector3

class Projection3D:
    def __init__(self,eye,right,up,forward,width,height,fov=70.,near=.05,far=2000.,orthographic=False,ortho_size=10.):
        self.eye = Vector3(eye.x,eye.y,eye.z)
        self.right,self.up,self.forward = right,up,forward
        self.width,self.height = max(1,width),max(1,height)
        self.near = max(.001,near);self.far = max(self.near+.001,far)
        self.orthographic,self.ortho_size = orthographic,max(.001,ortho_size)
        self.tany = math.tan(math.radians(max(1,min(179,fov)))*.5)
        self.tanx = self.tany*self.width/self.height
        self.focal = self.height*.5/self.tany
        self.scale = self.height/self.ortho_size
        self.halfy = self.ortho_size*.5;self.halfx = self.halfy*self.width/self.height

    @classmethod
    def from_camera(cls,camera,width,height):
        right,up,forward = camera.basis()
        return cls(camera.position,right,up,forward,width,height,camera.fov,camera.near,camera.far,camera.orthographic,camera.ortho_size)

    def view(self,point):
        rel = point-self.eye
        return Vector3(rel.dot(self.right),rel.dot(self.up),-rel.dot(self.forward))

    def project_view(self,v):
        depth = -v.z
        if depth < self.near-1e-7 or depth > self.far+1e-7:
            return None
        factor = self.scale if self.orthographic else self.focal/max(self.near,depth)
        return self.width*.5+v.x*factor,self.height*.5-v.y*factor,depth

    def project(self,point):
        return self.project_view(self.view(point))

    def units_per_pixel(self,point):
        return 1/self.scale if self.orthographic else max(self.near,-self.view(point).z)/self.focal

    def ray(self,x,y):
        if self.orthographic:
            origin = self.eye+self.right*((x-self.width*.5)/self.scale)+self.up*((self.height*.5-y)/self.scale)
            return origin,self.forward
        direction = self.forward+self.right*((x-self.width*.5)/self.focal)+self.up*((self.height*.5-y)/self.focal)
        return self.eye,direction.normalized

    def sphere_visible(self,center,radius):
        v = self.view(center);depth = -v.z
        if depth+radius < self.near or depth-radius > self.far:
            return False
        if self.orthographic:
            return abs(v.x)<=self.halfx+radius and abs(v.y)<=self.halfy+radius
        return (abs(v.x)<=depth*self.tanx+radius*math.sqrt(1+self.tanx*self.tanx)
                and abs(v.y)<=depth*self.tany+radius*math.sqrt(1+self.tany*self.tany))

    def clip(self,vertices):
        planes = [(0,0,-1,-self.near),(0,0,1,self.far)]
        if self.orthographic:
            planes += [(1,0,0,self.halfx),(-1,0,0,self.halfx),(0,1,0,self.halfy),(0,-1,0,self.halfy)]
        else:
            planes += [(1,0,-self.tanx,0),(-1,0,-self.tanx,0),(0,1,-self.tany,0),(0,-1,-self.tany,0)]
        result = vertices
        for a,b,c,d in planes:
            if not result:
                break
            output=[];previous=result[-1];pd=previous.x*a+previous.y*b+previous.z*c+d
            for current in result:
                cd=current.x*a+current.y*b+current.z*c+d
                if (cd>=0)!=(pd>=0):
                    output.append(previous.lerp(current,pd/(pd-cd)))
                if cd>=0:output.append(current)
                previous,pd=current,cd
            result=output
        return result

def visible_nodes(root):

    stack=[root]
    while stack:
        node=stack.pop()
        if not getattr(node,'visible',True):continue
        yield node
        stack.extend(reversed(node.get_children()))
