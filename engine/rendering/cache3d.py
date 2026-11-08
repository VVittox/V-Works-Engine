




from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from weakref import WeakKeyDictionary
from ..scene.node import Node3D
from ..utils.vmath import Vector3, rotate_euler
from .mesh3d import Mesh3D

IDENTITY = (1.,0.,0.,0., 0.,1.,0.,0., 0.,0.,1.,0.)

def xyz(v):
    return v.x, v.y, v.z

def point(matrix, v):
    x,y,z = v.x,v.y,v.z
    return Vector3(matrix[0]*x+matrix[1]*y+matrix[2]*z+matrix[3],
                   matrix[4]*x+matrix[5]*y+matrix[6]*z+matrix[7],
                   matrix[8]*x+matrix[9]*y+matrix[10]*z+matrix[11])

def multiply(a,b):
    return tuple(sum(a[row+k]*b[k*4+col] for k in range(3)) + (a[row+3] if col==3 else 0.)
                 for row in (0,4,8) for col in range(4))

class TransformCache3D:
    def __init__(self):
        self.entries = WeakKeyDictionary()

    def matrix(self, node):
        if node is None:
            return IDENTITY
        parent = self.matrix(node.parent)
        if not isinstance(node,Node3D):
            return parent
        key = xyz(node.position)+xyz(node.rotation)+xyz(node.scale)+(parent,)
        old = self.entries.get(node)
        if old is not None and old[0] == key:
            return old[1]
        x = rotate_euler(Vector3(node.scale.x,0,0),node.rotation)
        y = rotate_euler(Vector3(0,node.scale.y,0),node.rotation)
        z = rotate_euler(Vector3(0,0,node.scale.z),node.rotation)
        p = node.position
        local = (x.x,y.x,z.x,p.x, x.y,y.y,z.y,p.y, x.z,y.z,z.z,p.z)
        world = multiply(parent,local) if parent != IDENTITY else local
        self.entries[node] = key,world
        return world

@dataclass
class GeometryEntry:
    key: tuple
    matrix: tuple
    mesh: Mesh3D
    size: tuple
    offset: tuple
    center: Vector3
    radius: float
    vertices: list | None = None
    faces: list | None = None

    def prepare(self):
        if self.vertices is not None:
            return self
        sx,sy,sz = self.size;ox,oy,oz = self.offset
        self.vertices = [point(self.matrix,Vector3(v.x*sx+ox,v.y*sy+oy,v.z*sz+oz)) for v in self.mesh.vertices]
        self.faces = []
        for face in self.mesh.faces:
            if len(face)<3:
                continue
            verts = [self.vertices[i] for i in face]
            normal = (verts[1]-verts[0]).cross(verts[2]-verts[0]).normalized
            count = len(verts)
            center = Vector3(sum(v.x for v in verts)/count,sum(v.y for v in verts)/count,sum(v.z for v in verts)/count)
            self.faces.append((face,normal,center))
        return self

class GeometryCache3D:
    def __init__(self):
        self.transforms = TransformCache3D()
        self.nodes = WeakKeyDictionary()
        self.meshes = {}
        self.topologies = {}
        self.checked_files = {}

    def begin_frame(self):
        self.checked_files.clear()

    def mesh(self,node,project_dir):
        source = str(getattr(node,'mesh_path','') or '')
        if source:
            path = Path(source)
            path = path if path.is_absolute() else Path(project_dir)/path
            name = str(path)
            if name not in self.checked_files:
                try:
                    stat = path.stat();key = ('file',name,stat.st_mtime_ns,stat.st_size)
                    if key not in self.meshes:
                        mesh = Mesh3D.from_file(name)

                        for old in tuple(self.meshes):
                            if old[:2] == key[:2]:
                                removed = self.meshes.pop(old);self.topologies.pop(id(removed),None)
                        self.meshes[key] = mesh
                    self.checked_files[name] = self.meshes[key]
                except (OSError,ValueError,IndexError):
                    self.checked_files[name] = None
            mesh = self.checked_files[name]
            if mesh is not None:
                return mesh
        key = ('primitive',str(getattr(node,'primitive','cube')).lower(),int(getattr(node,'segments',14)),int(getattr(node,'rings',9)))
        if key not in self.meshes:
            self.meshes[key] = Mesh3D.from_primitive(*key[1:])
        return self.meshes[key]

    def topology(self,mesh):
        result = self.topologies.get(id(mesh))
        if result is None:
            if mesh.vertices:
                low = tuple(min(getattr(v,a) for v in mesh.vertices) for a in ('x','y','z'))
                high = tuple(max(getattr(v,a) for v in mesh.vertices) for a in ('x','y','z'))
            else:
                low = high = (0.,0.,0.)
            edges = set()
            for face in mesh.faces:
                for a,b in zip(face,face[1:]+face[:1]):
                    edges.add(tuple(sorted((a,b))))
            result = mesh,low,high,tuple(sorted(edges))
            self.topologies[id(mesh)] = result
        return result

    def entry(self,node,mesh,size=None,offset=None):
        matrix = self.transforms.matrix(node)
        size = xyz(size if size is not None else node.size)
        offset = xyz(offset) if offset is not None else (0.,0.,0.)
        key = (matrix,size,offset,id(mesh))
        old = self.nodes.get(node)
        if old is not None and old.key == key:
            return old
        _,lo,hi,_ = self.topology(mesh)
        corners = [point(matrix,Vector3(x*size[0]+offset[0],y*size[1]+offset[1],z*size[2]+offset[2]))
                   for x in (lo[0],hi[0]) for y in (lo[1],hi[1]) for z in (lo[2],hi[2])]
        low = Vector3(*(min(getattr(v,a) for v in corners) for a in ('x','y','z')))
        high = Vector3(*(max(getattr(v,a) for v in corners) for a in ('x','y','z')))
        old = GeometryEntry(key,matrix,mesh,size,offset,(low+high)*.5,(high-low).length*.5)
        self.nodes[node] = old
        return old
