from __future__ import annotations
import math
from pathlib import Path
from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QColor, QKeyEvent, QMouseEvent, QPainter, QPen, QWheelEvent
from PySide6.QtWidgets import QWidget
from engine.scene import Camera3DNode, DirectionalLight3D, PointLight3D, SpotLight3D, MeshInstance3D, Marker3D, RayCast3D, Node, Node3D, WorldEnvironment3D
from engine.rendering.mesh3d import Mesh3D
from engine.physics import PhysicsBody3D
from engine.utils.vmath import Vector3

class Viewport3D(QWidget):
    node_selected = Signal(object)
    node_changed = Signal(object)

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
        self._mesh_cache = {}
        self.project_dir = Path.cwd()
        self.setMinimumSize(520, 340)

    def set_project_dir(self, path) -> None:
        self.project_dir = Path(path).resolve()
        self._mesh_cache.clear()
        self.update()

    def set_scene(self, root: Node) -> None:
        self.scene_root = root
        self.update()

    def select_node(self, node: Node | None) -> None:
        self.selected = node
        self.update()

    def set_gizmo_mode(self, mode: str) -> None:
        self.gizmo_mode = mode
        self.update()

    def frame_selected(self) -> None:
        if isinstance(self.selected, Node3D):
            self.target = self.selected.global_position
            self.distance = max(3.0, min(80.0, self.distance))
            self.update()

    def toggle_pilot_camera(self) -> None:
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

    def _project(self, p: Vector3):
        eye, forward, right, up = self._basis()
        rel = p - eye
        depth = rel.dot(forward)
        if depth <= 0.02:
            return None
        camera = self._camera_for_pilot() if self.pilot_camera else None
        if camera is not None and camera.orthographic:
            factor = self.height() / max(0.001, camera.ortho_size)
            x = self.width() * 0.5 + rel.dot(right) * factor
            y = self.height() * 0.5 - rel.dot(up) * factor
            return QPointF(x, y), depth
        fov = camera.fov if camera is not None else self.fov
        focal = (self.height() * 0.5) / max(0.001, math.tan(math.radians(fov) * 0.5))
        x = self.width() * 0.5 + rel.dot(right) * focal / depth
        y = self.height() * 0.5 - rel.dot(up) * focal / depth
        return QPointF(x, y), depth

    def _mesh(self, node: MeshInstance3D) -> Mesh3D:
        if node.mesh_path:
            path = Path(node.mesh_path)
            if not path.is_absolute():
                path = self.project_dir / path
            try:
                key = (str(path.resolve()), path.stat().st_mtime_ns)
                mesh = self._mesh_cache.get(key)
                if mesh is None:
                    mesh = Mesh3D.from_file(str(path))
                    self._mesh_cache[key] = mesh
                return mesh
            except Exception:
                pass
        return Mesh3D.from_primitive(node.primitive, node.segments, node.rings)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.fillRect(self.rect(), QColor(28, 30, 35))
        if not self.pilot_camera:
            self._draw_grid(painter)
        if self.scene_root is not None:
            nodes = [n for n in self.scene_root.walk() if isinstance(n, Node3D) and n.visible]
            for node in nodes:
                self._draw_node(painter, node)
        painter.setPen(QColor(190, 195, 205))
        pilot = ' | CAMERA PREVIEW [P]' if self.pilot_camera else ' | P Camera Preview'
        painter.drawText(12, 22, f'3D | {self.gizmo_mode.title()} [W/E/R] | Orbit RMB | Pan MMB | Zoom Wheel{pilot}')

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

    def _draw_node(self, painter: QPainter, node: Node3D) -> None:
        selected = node is self.selected
        if isinstance(node, MeshInstance3D):
            mesh = self._mesh(node)
            size = node.size
            points3 = [node.to_global(Vector3(v.x * size.x, v.y * size.y, v.z * size.z)) for v in mesh.vertices]
            projected = [self._project(v) for v in points3]
            pen = QPen(QColor(255, 196, 75) if selected else QColor(*node.color), 2 if selected else 1)
            painter.setPen(pen)
            edges = set()
            for face in mesh.faces:
                for i in range(len(face)):
                    a, b = face[i], face[(i + 1) % len(face)]
                    edge = tuple(sorted((a, b)))
                    if edge in edges:
                        continue
                    edges.add(edge)
                    pa, pb = projected[a], projected[b]
                    if pa and pb:
                        painter.drawLine(pa[0], pb[0])
        elif isinstance(node, PhysicsBody3D):
            mesh = Mesh3D.cube()
            size = node.collider.size
            offset = node.collider.offset
            points3 = [node.to_global(offset + Vector3(v.x * size.x, v.y * size.y, v.z * size.z)) for v in mesh.vertices]
            projected = [self._project(v) for v in points3]
            painter.setPen(QPen(QColor(90, 230, 135) if not node.collider.is_trigger else QColor(235, 190, 80), 2 if selected else 1))
            edges = set()
            for face in mesh.faces:
                for i in range(len(face)):
                    a, b = face[i], face[(i + 1) % len(face)]
                    edge = tuple(sorted((a, b)))
                    if edge in edges:
                        continue
                    edges.add(edge)
                    pa, pb = projected[a], projected[b]
                    if pa and pb:
                        painter.drawLine(pa[0], pb[0])
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
        if self.scene_root is None:
            return None
        best = None
        best_dist = 22.0
        for node in self.scene_root.walk():
            if not isinstance(node, Node3D) or not node.visible:
                continue
            pr = self._project(node.global_position)
            if not pr:
                continue
            d = math.hypot(pr[0].x() - pos.x(), pr[0].y() - pos.y())
            if d < best_dist:
                best_dist = d
                best = node
        return best

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self._last = event.position()
        if event.button() == Qt.RightButton:
            if not self.pilot_camera:
                self._orbiting = True
            return
        if event.button() == Qt.MiddleButton:
            if not self.pilot_camera:
                self._panning = True
            return
        if event.button() == Qt.LeftButton:
            hit = self._hit_test(event.position())
            if hit is not None:
                self.selected = hit
                self.node_selected.emit(hit)
                self._dragging = not hit.editor_locked and not self.pilot_camera
            else:
                self._dragging = False
            self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        p = event.position()
        dx, dy = p.x() - self._last.x(), p.y() - self._last.y()
        self._last = p
        if self._orbiting:
            self.yaw += dx * 0.008
            self.pitch = max(math.radians(-89), min(math.radians(89), self.pitch - dy * 0.008))
            self.update()
            return
        if self._panning:
            _, _, right, up = self._basis()
            scale = self.distance / max(300.0, self.height())
            self.target = self.target - right * (dx * scale) + up * (dy * scale)
            self.update()
            return
        if self._dragging and isinstance(self.selected, Node3D):
            if self.gizmo_mode == 'move':
                scale = self.distance / max(300.0, self.height()) * 2.0
                self.selected.position.x += dx * scale
                if event.modifiers() & Qt.ShiftModifier:
                    self.selected.position.y -= dy * scale
                else:
                    self.selected.position.z += dy * scale
                if self.snap_enabled:
                    snap = max(0.001, self.snap_size)
                    self.selected.position.x = round(self.selected.position.x / snap) * snap
                    self.selected.position.y = round(self.selected.position.y / snap) * snap
                    self.selected.position.z = round(self.selected.position.z / snap) * snap
            elif self.gizmo_mode == 'rotate':
                self.selected.rotation.y += dx * 0.01
                if event.modifiers() & Qt.ShiftModifier:
                    self.selected.rotation.z += dy * 0.01
                else:
                    self.selected.rotation.x += dy * 0.01
                if self.snap_enabled:
                    snap = math.radians(15.0)
                    self.selected.rotation.x = round(self.selected.rotation.x / snap) * snap
                    self.selected.rotation.y = round(self.selected.rotation.y / snap) * snap
                    self.selected.rotation.z = round(self.selected.rotation.z / snap) * snap
            elif self.gizmo_mode == 'scale':
                factor = max(0.01, 1.0 + (dx - dy) * 0.01)
                self.selected.scale = self.selected.scale * factor
                if self.snap_enabled:
                    snap = max(0.05, self.snap_size)
                    self.selected.scale.x = max(0.001, round(self.selected.scale.x / snap) * snap)
                    self.selected.scale.y = max(0.001, round(self.selected.scale.y / snap) * snap)
                    self.selected.scale.z = max(0.001, round(self.selected.scale.z / snap) * snap)
            self.node_changed.emit(self.selected)
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.RightButton:
            self._orbiting = False
        elif event.button() == Qt.MiddleButton:
            self._panning = False
        elif event.button() == Qt.LeftButton:
            self._dragging = False

    def wheelEvent(self, event: QWheelEvent) -> None:
        if self.pilot_camera:
            camera = self._camera_for_pilot()
            if camera is not None and not camera.orthographic:
                camera.fov = max(10.0, min(150.0, camera.fov + (-2.0 if event.angleDelta().y() > 0 else 2.0)))
                self.node_changed.emit(camera)
                self.update()
            return
        factor = 0.88 if event.angleDelta().y() > 0 else 1.14
        self.distance = max(0.5, min(500.0, self.distance * factor))
        self.update()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key_W:
            self.set_gizmo_mode('move')
        elif event.key() == Qt.Key_E:
            self.set_gizmo_mode('rotate')
        elif event.key() == Qt.Key_R:
            self.set_gizmo_mode('scale')
        elif event.key() == Qt.Key_F:
            self.frame_selected()
        elif event.key() == Qt.Key_P:
            self.toggle_pilot_camera()
        else:
            super().keyPressEvent(event)
