from __future__ import annotations
import math
from pathlib import Path
from PySide6.QtCore import QPointF, QLineF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QKeyEvent, QMouseEvent, QPainter, QPen, QPolygonF, QWheelEvent
from PySide6.QtWidgets import QWidget
from engine.scene import Camera3DNode, DirectionalLight3D, PointLight3D, SpotLight3D, MeshInstance3D, Marker3D, RayCast3D, Node, Node3D, WorldEnvironment3D
from engine.rendering.mesh3d import Mesh3D
from engine.physics import PhysicsBody3D
from engine.utils.vmath import Vector3
from engine.rendering.cache3d import GeometryCache3D
from engine.rendering.projection3d import Projection3D, visible_nodes
from editor.transform_gizmo import TransformDrag, axes_for, triangle_hit

class Viewport3D(QWidget):
    node_selected = Signal(object)
    node_changed = Signal(object)
    transform_started = Signal(object)
    transform_finished = Signal(object, bool)
    snap_changed = Signal(bool)
    mode_changed = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.scene_root: Node | None = None
        self.selected: Node | None = None
        self.target = Vector3()
        self.yaw = math.radians(35.0)
        self.pitch = math.radians(-22.0)
        self.distance = 12.0
        self.fov = 65.0
        self.gizmo_mode = 'move'
        self.snap_enabled = False
        self.snap_size = 0.5
        self.pilot_camera = False
        self._orbiting = False
        self._panning = False
        self._dragging = False
        self._last = QPointF()
        self._geometry = GeometryCache3D()
        self._projection = None
        self._drag = None
        self.local_space = False
        self._hover_handle = None
        self._gizmo_handles = []
        self._shown = self._culled = 0
        self.project_dir = Path.cwd()
        self.setMinimumSize(520, 340)

    def set_project_dir(self, path) -> None:
        self.project_dir = Path(path).resolve()
        self._geometry = GeometryCache3D()
        self.update()

    def set_scene(self, root: Node) -> None:
        self.cancel_transform()
        self.scene_root = root
        self.update()

    def select_node(self, node: Node | None) -> None:
        if node is not self.selected:self.cancel_transform()
        self.selected = node
        self.update()

    def set_gizmo_mode(self, mode: str) -> None:
        changed=mode != self.gizmo_mode
        if changed:self.cancel_transform()
        self.gizmo_mode = mode
        if changed:self.mode_changed.emit(mode)
        self.update()

    def frame_selected(self) -> None:
        if isinstance(self.selected, Node3D):
            self.target = self.selected.global_position
            radius = .8
            if isinstance(self.selected,(MeshInstance3D,PhysicsBody3D)):
                entry = self._entry(self.selected)
                self.target=entry.center;radius=max(.3,entry.radius)
            self.distance = max(1., min(500., radius/max(.05,math.tan(math.radians(self.fov)*.5))*1.5))
            self.update()

    def toggle_pilot_camera(self) -> None:
        self.cancel_transform()
        self.pilot_camera = not self.pilot_camera
        self.update()

    def _camera_for_pilot(self):
        if isinstance(self.selected, Camera3DNode):
            return self.selected
        if self.scene_root is not None:
            return next((n for n in self.scene_root.walk() if isinstance(n, Camera3DNode) and n.current and n.visible), None)
        return None

    def _basis(self):
        if self.pilot_camera:
            camera = self._camera_for_pilot()
            if camera is not None:
                forward = camera.global_forward.normalized
                up_hint = camera.global_up.normalized
                right = forward.cross(up_hint).normalized
                if not right.length:
                    right = camera.global_right.normalized
                up = right.cross(forward).normalized
                return camera.global_position, forward, right, up
        cp = math.cos(self.pitch)
        forward = Vector3(math.sin(self.yaw) * cp, math.sin(self.pitch), -math.cos(self.yaw) * cp).normalized
        eye = self.target - forward * self.distance
        right = forward.cross(Vector3.UP()).normalized
        if not right.length:
            right = Vector3.RIGHT()
        up = right.cross(forward).normalized
        return eye, forward, right, up

    def _refresh_projection(self):
        eye,forward,right,up=self._basis()
        camera = self._camera_for_pilot() if self.pilot_camera else None
        self._projection=Projection3D(eye,right,up,forward,self.width(),self.height(),
            camera.fov if camera else self.fov,camera.near if camera else .02,camera.far if camera else 10000.,
            camera.orthographic if camera else False,camera.ortho_size if camera else 10.)
        return self._projection

    def _project(self, p: Vector3):
        projection=self._projection or self._refresh_projection();value=projection.project(p)
        return (QPointF(value[0],value[1]),value[2]) if value else None

    def _mesh(self, node: MeshInstance3D) -> Mesh3D:
        return self._geometry.mesh(node,self.project_dir)

    def _entry(self,node):
        mesh=self._mesh(node)
        if isinstance(node,PhysicsBody3D):
            return self._geometry.entry(node,mesh,node.collider.size,node.collider.offset)
        return self._geometry.entry(node,mesh)

    def paintEvent(self, event) -> None:
        self._refresh_projection();self._geometry.begin_frame();self._shown=self._culled=0
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.fillRect(self.rect(), QColor(28, 30, 35))
        if not self.pilot_camera:
            self._draw_grid(painter)
        if self.scene_root is not None:
            nodes = [n for n in visible_nodes(self.scene_root) if isinstance(n, Node3D)]
            for node in nodes:
                self._draw_node(painter, node)
        self._draw_gizmo(painter)
        painter.fillRect(QRectF(0,0,self.width(),76),QColor(24,27,34,235))
        painter.setPen(QColor(190, 195, 205))
        pilot = ' | CAMERA PREVIEW [P]' if self.pilot_camera else ' | P Camera Preview'
        painter.drawText(12, 22, f'3D | {self.gizmo_mode.title()} [W/E/R] | Orbit RMB | Pan MMB | F Frame{pilot}')
        for rect,text in self._toolbar():
            painter.fillRect(QRectF(*rect),QColor(48,56,70));painter.setPen(QColor(219,225,236))
            painter.drawText(QRectF(*rect),Qt.AlignCenter,text)
        painter.fillRect(QRectF(0,self.height()-30,self.width(),30),QColor(24,27,34,235))
        painter.setPen(QColor(187,202,219))
        if self._drag:
            p=self.selected.position
            message=f'{self._drag.constraint} | X / Y / Z axis, Shift+axis plane | Ctrl snap | Shift precision | Esc cancel | {p.x:.3f}, {p.y:.3f}, {p.z:.3f}'
        else:message=f'Drag arrows / planes / center | L World/Local | Shown {self._shown} | Culled {self._culled}'
        painter.drawText(12,self.height()-10,message)

    def _toolbar(self):
        space='LOCAL' if self.local_space or self.gizmo_mode!='move' else 'WORLD'
        return [((12,39,98,25),space+' [L]'),((118,39,132,25),f'Snap {self.snap_size:g}: '+('ON' if self.snap_enabled else 'Ctrl')),
                ((258,39,28,25),'−'),((292,39,28,25),'+')]

    def _draw_grid(self, painter: QPainter) -> None:
        extent = 20
        for i in range(-extent, extent + 1):
            a = self._project(Vector3(i, 0, -extent))
            b = self._project(Vector3(i, 0, extent))
            c = self._project(Vector3(-extent, 0, i))
            d = self._project(Vector3(extent, 0, i))
            color = QColor(60, 64, 72) if i == 0 else QColor(43, 46, 53)
            painter.setPen(QPen(color, 1))
            if a and b:
                painter.drawLine(a[0], b[0])
            if c and d:
                painter.drawLine(c[0], d[0])
        origin = self._project(Vector3())
        x = self._project(Vector3(2, 0, 0))
        y = self._project(Vector3(0, 2, 0))
        z = self._project(Vector3(0, 0, 2))
        if origin:
            if x:
                painter.setPen(QPen(QColor(220, 80, 90), 2)); painter.drawLine(origin[0], x[0])
            if y:
                painter.setPen(QPen(QColor(90, 220, 120), 2)); painter.drawLine(origin[0], y[0])
            if z:
                painter.setPen(QPen(QColor(80, 145, 235), 2)); painter.drawLine(origin[0], z[0])

    def _draw_camera_frustum(self, painter: QPainter, node: Camera3DNode) -> None:
        near = max(0.08, node.near)
        far = max(near + 0.1, min(node.far, near + 5.0))
        aspect = max(0.2, self.width() / max(1, self.height()))
        if node.orthographic:
            nh = fh = node.ortho_size * 0.5
            nw = fw = nh * aspect
        else:
            nh = math.tan(math.radians(node.fov) * 0.5) * near
            nw = nh * aspect
            fh = math.tan(math.radians(node.fov) * 0.5) * far
            fw = fh * aspect
        local = [
            Vector3(-nw, -nh, -near), Vector3(nw, -nh, -near), Vector3(nw, nh, -near), Vector3(-nw, nh, -near),
            Vector3(-fw, -fh, -far), Vector3(fw, -fh, -far), Vector3(fw, fh, -far), Vector3(-fw, fh, -far),
        ]
        pts = [self._project(node.to_global(v)) for v in local]
        if any(p is None for p in pts):
            return
        q = [p[0] for p in pts]
        painter.setPen(QPen(QColor(120, 210, 255, 150), 1))
        for ring in ((0,1,2,3,0), (4,5,6,7,4)):
            for a, b in zip(ring, ring[1:]):
                painter.drawLine(q[a], q[b])
        for i in range(4):
            painter.drawLine(q[i], q[i + 4])

    def _draw_geometry(self,painter,node):
        entry=self._entry(node)
        if not self._projection.sphere_visible(entry.center,entry.radius):
            self._culled+=1;return
        self._shown+=1;entry.prepare()
        points=[self._project(v) for v in entry.vertices]
        color=(255,196,75) if node is self.selected else ((235,190,80) if node.collider.is_trigger else (90,230,135)) if isinstance(node,PhysicsBody3D) else node.color
        painter.setPen(QPen(QColor(*color),2 if node is self.selected else 1))
        lines=[]
        for a,b in self._geometry.topology(entry.mesh)[3]:
            pa,pb=points[a],points[b]
            if pa and pb:lines.append(QLineF(pa[0],pb[0]))
        if lines:painter.drawLines(lines)

    def _layout_gizmo(self):
        self._gizmo_handles=[]
        node=self.selected
        if not isinstance(node,Node3D) or self.pilot_camera or node.editor_locked:return None
        origin=node.global_position;p=self._project(origin)
        if not p:return None
        length=self._projection.units_per_pixel(origin)*94
        axes=axes_for(node,self.local_space if self.gizmo_mode=='move' else True)
        ends={key:self._project(origin+axis*length) for key,axis in axes.items()}
        self._gizmo_handles.append(('VIEW','center',p[0]))
        if self.gizmo_mode=='move':
            for plane in ('XY','XZ','YZ'):
                a,b=(axes[key]*length for key in plane)
                points=[self._project(origin+a*x+b*y) for x,y in ((.19,.19),(.40,.19),(.40,.40),(.19,.40))]
                if all(points):
                    poly=QPolygonF([q[0] for q in points]);self._gizmo_handles.append((plane,'plane',poly))
        for key,end in ends.items():
            if end and math.hypot(end[0].x()-p[0].x(),end[0].y()-p[0].y())>16:
                self._gizmo_handles.append((key,'axis',(p[0],end[0])))
        return p[0]

    def _draw_gizmo(self,painter):
        center=self._layout_gizmo()
        if center is None:return
        colors={'X':(238,91,100),'Y':(103,220,133),'Z':(95,163,251),'XY':(230,195,82),'XZ':(190,114,235),'YZ':(78,204,211)}
        active=self._drag.constraint if self._drag else self._hover_handle
        for key,kind,data in self._gizmo_handles:
            if kind!='plane':continue
            color=(255,226,130) if key==active else colors[key]
            painter.setPen(QPen(QColor(*color),1));painter.setBrush(QColor(*color,105 if key==active else 45));painter.drawPolygon(data)
        for key,kind,data in self._gizmo_handles:
            if kind!='axis':continue
            a,b=data;color=(255,226,130) if key==active else colors[key]
            painter.setPen(QPen(QColor(12,16,22,210),6));painter.drawLine(a,b)
            painter.setPen(QPen(QColor(*color),3));painter.drawLine(a,b);painter.setBrush(QColor(*color))
            dx,dy=b.x()-a.x(),b.y()-a.y();length=max(1,math.hypot(dx,dy));dx/=length;dy/=length
            if self.gizmo_mode=='scale':painter.drawRect(QRectF(b.x()-5,b.y()-5,10,10))
            elif self.gizmo_mode=='rotate':painter.drawEllipse(b,7,7)
            else:painter.drawPolygon(QPolygonF([b,QPointF(b.x()-dx*13+dy*5,b.y()-dy*13-dx*5),QPointF(b.x()-dx*13-dy*5,b.y()-dy*13+dx*5)]))
            painter.drawText(QPointF(b.x()+8,b.y()-6),key)
        painter.setPen(QPen(QColor(255,226,130) if active=='VIEW' else QColor(228,234,244),2))
        painter.setBrush(QColor(39,45,57));painter.drawRect(QRectF(center.x()-5,center.y()-5,10,10))
        painter.setBrush(Qt.NoBrush)

    def _hit_gizmo(self,pos):
        self._layout_gizmo()

        for key,kind,data in self._gizmo_handles:
            if kind=='center' and math.hypot(pos.x()-data.x(),pos.y()-data.y())<9:return key
            if kind=='plane' and data.containsPoint(pos,Qt.OddEvenFill):return key
        best=None;distance=10.
        for key,kind,data in self._gizmo_handles:
            if kind!='axis':continue
            a,b=data;dx,dy=b.x()-a.x(),b.y()-a.y();length=dx*dx+dy*dy
            t=max(.12,min(1.,((pos.x()-a.x())*dx+(pos.y()-a.y())*dy)/max(1,length)))
            d=math.hypot(pos.x()-a.x()-t*dx,pos.y()-a.y()-t*dy)
            if d<distance:best,distance=key,d
        return best

    def _draw_node(self, painter: QPainter, node: Node3D) -> None:
        selected = node is self.selected
        if isinstance(node, (MeshInstance3D,PhysicsBody3D)):
            self._draw_geometry(painter,node)
        else:
            p = self._project(node.global_position)
            if not p:
                return
            c = p[0]
            if isinstance(node, Camera3DNode):
                painter.setPen(QPen(QColor(120, 210, 255), 2))
                painter.drawRect(int(c.x() - 8), int(c.y() - 6), 16, 12)
                f = self._project(node.global_position + node.global_forward * 1.2)
                if f:
                    painter.drawLine(c, f[0])
                if selected or node.current:
                    self._draw_camera_frustum(painter, node)
            elif isinstance(node, DirectionalLight3D):
                painter.setPen(QPen(QColor(255, 225, 100), 2))
                painter.drawEllipse(c, 6, 6)
                f = self._project(node.global_position + node.direction * 1.5)
                if f:
                    painter.drawLine(c, f[0])
            elif isinstance(node, SpotLight3D):
                painter.setPen(QPen(QColor(*node.color), 2))
                painter.drawEllipse(c, 6, 6)
                end = self._project(node.global_position + node.direction * min(node.range, 4.0))
                if end:
                    painter.drawLine(c, end[0])
            elif isinstance(node, PointLight3D):
                painter.setPen(QPen(QColor(*node.color), 2))
                painter.drawEllipse(c, 6, 6)
                edge = self._project(node.global_position + Vector3(min(node.range, 4.0), 0, 0))
                if edge:
                    r = max(4.0, math.hypot(edge[0].x() - c.x(), edge[0].y() - c.y()))
                    painter.setPen(QPen(QColor(*node.color, 100), 1))
                    painter.drawEllipse(c, r, r)
            elif isinstance(node, RayCast3D):
                end = self._project(node.to_global(node.target_position))
                painter.setPen(QPen(QColor(90, 230, 135) if node.colliding else QColor(235, 190, 80), 2))
                painter.drawEllipse(c, 4, 4)
                if end:
                    painter.drawLine(c, end[0])
            elif isinstance(node, Marker3D):
                painter.setPen(QPen(QColor(210, 120, 255), 2))
                painter.drawLine(QPointF(c.x() - 7, c.y()), QPointF(c.x() + 7, c.y()))
                painter.drawLine(QPointF(c.x(), c.y() - 7), QPointF(c.x(), c.y() + 7))
            elif isinstance(node, WorldEnvironment3D):
                painter.setPen(QPen(QColor(150, 180, 220), 2))
                painter.drawEllipse(c, 8, 8)
            else:
                painter.setPen(QPen(QColor(255, 196, 75) if selected else QColor(190, 195, 205), 2))
                painter.drawEllipse(c, 5, 5)
        if selected:
            p = self._project(node.global_position)
            if p:
                c = p[0]
                painter.setPen(QPen(QColor(255, 196, 75), 2))
                painter.drawEllipse(c, 10, 10)

    def _hit_test(self, pos: QPointF) -> Node3D | None:
        if self.scene_root is None:return None
        ray=self._projection.ray(pos.x(),pos.y());best=None;nearest=float('inf')
        for node in visible_nodes(self.scene_root):
            if not isinstance(node,Node3D):continue
            if isinstance(node,(MeshInstance3D,PhysicsBody3D)):
                entry=self._entry(node);delta=entry.center-ray[0];along=delta.dot(ray[1])
                if along+entry.radius<0 or delta.dot(delta)-along*along>entry.radius**2:continue
                entry.prepare()
                for face,_,_ in entry.faces:
                    for i in range(1,len(face)-1):
                        hit=triangle_hit(ray,entry.vertices[face[0]],entry.vertices[face[i]],entry.vertices[face[i+1]])
                        if hit is not None and hit<nearest:best,nearest=node,hit
            else:
                pr=self._project(node.global_position)
                if pr and math.hypot(pr[0].x()-pos.x(),pr[0].y()-pos.y())<14 and pr[1]<nearest:
                    best,nearest=node,pr[1]
        return best

    def _begin_transform(self,pos,constraint='VIEW'):
        if self._drag is not None:return
        if not isinstance(self.selected,Node3D) or self.selected.editor_locked or self.pilot_camera:return
        if any(abs(value)<1e-9 for value in (self.selected.global_scale.x,self.selected.global_scale.y,self.selected.global_scale.z)):
            return
        self.transform_started.emit(self.selected)
        self._drag=TransformDrag(self.selected,self._projection,(pos.x(),pos.y()),self.gizmo_mode,constraint,self.local_space)
        self._dragging=True;self.setCursor(Qt.ClosedHandCursor)

    def _finish_transform(self,commit=True):
        if self._drag is None:return False
        drag=self._drag;changed=drag.changed
        self._drag=None;self._dragging=False
        if not commit:drag.cancel();self.node_changed.emit(drag.node)
        self.transform_finished.emit(drag.node,bool(commit and changed))
        self.unsetCursor();self.update();return True

    def cancel_transform(self):
        return self._finish_transform(False)

    def commit_transform(self):
        return self._finish_transform(True)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self.setFocus(Qt.MouseFocusReason);self._last=event.position();self._refresh_projection();self._geometry.begin_frame()
        if event.button()==Qt.RightButton:
            if self._drag:self.cancel_transform();return
            if not self.pilot_camera:self._orbiting=True
            return
        if event.button()==Qt.MiddleButton:
            if not self.pilot_camera and not self._drag:self._panning=True
            return
        if event.button()!=Qt.LeftButton:return
        if self._drag:self.commit_transform();return
        pos=event.position()
        for i,(rect,_) in enumerate(self._toolbar()):
            if QRectF(*rect).contains(pos):
                self.cancel_transform()
                if i==0:self.local_space=not self.local_space
                elif i==1:
                    self.snap_enabled=not self.snap_enabled;self.snap_changed.emit(self.snap_enabled)
                else:self.snap_size=max(.001,min(1000.,self.snap_size*(.5 if i==2 else 2.)))
                self.update();return
        constraint=self._hit_gizmo(pos)
        if constraint is not None:self._begin_transform(pos,constraint);return
        hit=self._hit_test(pos)
        if hit is not None:
            self.selected=hit;self.node_selected.emit(hit)


        self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        p=event.position();dx,dy=p.x()-self._last.x(),p.y()-self._last.y();self._last=p
        if self._orbiting:
            self.yaw+=dx*.008;self.pitch=max(math.radians(-89),min(math.radians(89),self.pitch-dy*.008));self.update();return
        if self._panning:
            _,_,right,up=self._basis();scale=self.distance/max(300.,self.height())
            self.target=self.target-right*(dx*scale)+up*(dy*scale);self.update();return
        if self._drag:
            enabled=self.snap_enabled or bool(event.modifiers() & Qt.ControlModifier)
            self._drag.update((p.x(),p.y()),self.snap_size if enabled else 0.,bool(event.modifiers() & Qt.ShiftModifier))
            self.node_changed.emit(self.selected);self.update();return
        self._refresh_projection();hover=self._hit_gizmo(p)
        if hover!=self._hover_handle:
            self._hover_handle=hover
            if hover:self.setCursor(Qt.OpenHandCursor)
            else:self.unsetCursor()
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button()==Qt.RightButton:self._orbiting=False
        elif event.button()==Qt.MiddleButton:self._panning=False
        elif event.button()==Qt.LeftButton:self._finish_transform(True)

    def wheelEvent(self, event: QWheelEvent) -> None:
        if self._drag:return
        if self.pilot_camera:
            camera=self._camera_for_pilot()
            if camera is not None and not camera.orthographic:
                camera.fov=max(10.,min(150.,camera.fov+(-2. if event.angleDelta().y()>0 else 2.)))
                self.node_changed.emit(camera);self.update()
            return
        factor=.88 if event.angleDelta().y()>0 else 1.14
        self.distance=max(.5,min(500.,self.distance*factor));self.update()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        key=event.key()
        if key==Qt.Key_Escape and self.cancel_transform():event.accept();return
        if key in (Qt.Key_X,Qt.Key_Y,Qt.Key_Z) and self._drag:
            axis={Qt.Key_X:'X',Qt.Key_Y:'Y',Qt.Key_Z:'Z'}[key]
            constraint=''.join(a for a in 'XYZ' if a!=axis) if self.gizmo_mode=='move' and event.modifiers() & Qt.ShiftModifier else axis
            self._drag.set_constraint('VIEW' if self._drag.constraint==constraint else constraint)
            enabled=self.snap_enabled or bool(event.modifiers() & Qt.ControlModifier)
            self._drag.update((self._last.x(),self._last.y()),self.snap_size if enabled else 0.,bool(event.modifiers() & Qt.ShiftModifier))
            self.node_changed.emit(self.selected);self.update();return
        if key==Qt.Key_L:
            self.cancel_transform();self.local_space=not self.local_space;self.update()
        elif key==Qt.Key_G:
            self.set_gizmo_mode('move');self._refresh_projection();self._begin_transform(self._last)
        elif key==Qt.Key_Return and self._drag:self._finish_transform(True)
        elif key==Qt.Key_W:self.set_gizmo_mode('move')
        elif key==Qt.Key_E:self.set_gizmo_mode('rotate')
        elif key==Qt.Key_R:self.set_gizmo_mode('scale')
        elif key==Qt.Key_F:self.frame_selected()
        elif key==Qt.Key_P:self.toggle_pilot_camera()
        else:super().keyPressEvent(event)

    def focusOutEvent(self,event):
        self.cancel_transform();self._orbiting=self._panning=False;super().focusOutEvent(event)
