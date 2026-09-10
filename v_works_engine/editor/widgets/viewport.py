from __future__ import annotations
import math
from pathlib import Path
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QDragEnterEvent, QDropEvent, QKeyEvent, QMouseEvent, QPainter, QPen, QPixmap, QTransform, QWheelEvent
from PySide6.QtWidgets import QWidget
from engine.scene import Button2D, Camera2DNode, CollisionRect2D, ColorRect2D, Label2D, Node, Node2D, Sprite2D, TileMap2D, ParticleSystem2D, Light2D, Control, UIPanel, UILabel, Navigation2D, NavigationAgent2D
from engine.physics import PhysicsBody2D
from engine.utils.vmath import Vector2

class Viewport2D(QWidget):
    node_selected = Signal(object)
    node_changed = Signal(object)
    asset_dropped = Signal(str, object)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setAcceptDrops(True)
        self.scene_root: Node | None = None
        self.selected: Node | None = None
        self.project_dir = Path.cwd()
        self.zoom = 1.0
        self.pan = QPointF(0, 0)
        self._dragging_node = False
        self._panning = False
        self._last_mouse = QPointF()
        self._edit_dirty = False
        self.snap_enabled = False
        self.snap_size = 16.0
        self.rotation_snap_degrees = 15.0
        self.gizmo_mode = 'move'
        self.show_collision = True
        self.show_camera_frames = True
        self.show_origin = True
        self._pixmaps: dict[str, QPixmap] = {}
        self.game_size = (1280, 720)
        self.tile_paint_enabled = False
        self.tile_paint_index = 0
        self.setMinimumSize(520, 340)

    def set_tile_paint(self, enabled: bool, tile: int=0) -> None:
        self.tile_paint_enabled = bool(enabled)
        self.tile_paint_index = int(tile)
        self.update()

    def set_game_size(self, width: int, height: int) -> None:
        self.game_size = (max(1, int(width)), max(1, int(height)))
        self.update()

    def set_project_dir(self, path: str | Path) -> None:
        self.project_dir = Path(path).resolve()
        self._pixmaps.clear()
        self.update()

    def set_scene(self, root: Node) -> None:
        self.scene_root = root
        self.selected = root
        self.update()

    def select_node(self, node: Node | None) -> None:
        self.selected = node
        self.update()

    def set_gizmo_mode(self, mode: str) -> None:
        if mode in {'move', 'rotate', 'scale'}:
            self.gizmo_mode = mode
            self.update()

    def frame_selected(self) -> None:
        if isinstance(self.selected, Node2D):
            p = self.selected.global_position
            self.pan = QPointF(-p.x * self.zoom, -p.y * self.zoom)
            self.update()

    def _world_to_screen(self, x: float, y: float) -> QPointF:
        center = QPointF(self.width() / 2, self.height() / 2)
        return QPointF(center.x() + self.pan.x() + x * self.zoom, center.y() + self.pan.y() + y * self.zoom)

    def _screen_to_world(self, p: QPointF) -> QPointF:
        center = QPointF(self.width() / 2, self.height() / 2)
        return QPointF((p.x() - center.x() - self.pan.x()) / self.zoom, (p.y() - center.y() - self.pan.y()) / self.zoom)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        painter.fillRect(self.rect(), QColor(31, 33, 38))
        self._draw_grid(painter)
        if self.scene_root is not None:
            nodes = [n for n in self.scene_root.walk() if isinstance(n, Node2D) and n.visible]
            nodes.sort(key=lambda n: n.z_index)
            for node in nodes:
                self._draw_node(painter, node)
        painter.setPen(QColor(185, 190, 200))
        snap = f' | Snap {self.snap_size:g}px' if self.snap_enabled else ''
        painter.drawText(12, 22, f'2D | {self.gizmo_mode.title()} [W/E/R] | Zoom {self.zoom:.2f}x{snap}')

    def _draw_grid(self, painter: QPainter) -> None:
        base = 16.0 if self.snap_enabled else 32.0
        spacing = max(8.0, base * self.zoom)
        while spacing < 20:
            spacing *= 2
        origin = self._world_to_screen(0, 0)
        painter.setPen(QPen(QColor(45, 48, 55), 1))
        x = origin.x() % spacing
        while x < self.width():
            painter.drawLine(int(x), 0, int(x), self.height())
            x += spacing
        y = origin.y() % spacing
        while y < self.height():
            painter.drawLine(0, int(y), self.width(), int(y))
            y += spacing
        if self.show_origin:
            painter.setPen(QPen(QColor(72, 76, 88), 1))
            painter.drawLine(0, int(origin.y()), self.width(), int(origin.y()))
            painter.drawLine(int(origin.x()), 0, int(origin.x()), self.height())

    def _resolve(self, text: str) -> Path:
        p = Path(text)
        return p if p.is_absolute() else self.project_dir / p

    def _pixmap(self, path: str) -> QPixmap | None:
        resolved = str(self._resolve(path).resolve())
        if resolved not in self._pixmaps:
            pm = QPixmap(resolved)
            self._pixmaps[resolved] = pm
        pm = self._pixmaps[resolved]
        return pm if not pm.isNull() else None

    def _node_rect(self, node: Node2D) -> QRectF:
        p = self._world_to_screen(node.global_position.x, node.global_position.y)
        if isinstance(node, (ColorRect2D, Button2D)):
            w, h = (abs(node.size.x * node.global_scale.x * self.zoom), abs(node.size.y * node.global_scale.y * self.zoom))
            return QRectF(p.x(), p.y(), max(6, w), max(6, h))
        if isinstance(node, Sprite2D) and node.texture_path:
            pm = self._pixmap(node.texture_path)
            if pm:
                w, h = (abs(pm.width() * node.global_scale.x * self.zoom), abs(pm.height() * node.global_scale.y * self.zoom))
                return QRectF(p.x() - w / 2 if node.centered else p.x(), p.y() - h / 2 if node.centered else p.y(), max(6, w), max(6, h))
        if isinstance(node, TileMap2D):
            cells = list(node.iter_tiles())
            if cells:
                xs = [x for x, _, _ in cells]
                ys = [y for _, y, _ in cells]
                w = (max(xs) - min(xs) + 1) * node.tile_size.x * abs(node.global_scale.x) * self.zoom
                h = (max(ys) - min(ys) + 1) * node.tile_size.y * abs(node.global_scale.y) * self.zoom
                start = self._world_to_screen(node.global_position.x + min(xs) * node.tile_size.x, node.global_position.y + min(ys) * node.tile_size.y)
                return QRectF(start.x(), start.y(), max(12, w), max(12, h))
            return QRectF(p.x() - 10, p.y() - 10, 20, 20)
        if isinstance(node, Light2D):
            r = max(8, node.radius * self.zoom)
            return QRectF(p.x() - r, p.y() - r, r * 2, r * 2)
        if isinstance(node, Control):
            from engine.utils.vmath import Vector2
            pos, size = node.resolved_rect(Vector2(*self.game_size))
            q = self._world_to_screen(pos.x, pos.y)
            return QRectF(q.x(), q.y(), max(6, size.x * self.zoom), max(6, size.y * self.zoom))
        if isinstance(node, Navigation2D):
            return QRectF(p.x(), p.y(), max(12, node.width * node.cell_size * self.zoom), max(12, node.height * node.cell_size * self.zoom))
        if isinstance(node, CollisionRect2D):
            w, h = (abs(node.size.x * node.scale.x * self.zoom), abs(node.size.y * node.scale.y * self.zoom))
            return QRectF(p.x(), p.y(), max(6, w), max(6, h))
        if isinstance(node, PhysicsBody2D):
            w, h = (abs(node.collider.size.x * node.global_scale.x * self.zoom), abs(node.collider.size.y * node.global_scale.y * self.zoom))
            return QRectF(p.x(), p.y(), max(12, w), max(12, h))
        if isinstance(node, Camera2DNode):
            return QRectF(p.x() - 12, p.y() - 12, 24, 24)
        if isinstance(node, Label2D):
            return QRectF(p.x(), p.y(), max(50, len(node.text) * node.font_size * 0.55 * self.zoom), max(20, node.font_size * self.zoom))
        return QRectF(p.x() - 12 * self.zoom, p.y() - 12 * self.zoom, max(12, 24 * self.zoom), max(12, 24 * self.zoom))

    def _draw_node(self, painter: QPainter, node: Node2D) -> None:
        rect = self._node_rect(node)
        if isinstance(node, Button2D):
            painter.fillRect(rect, QColor(*node.color))
            painter.setPen(QColor(*node.text_color))
            painter.drawText(rect.adjusted(10, 4, -4, -4), Qt.AlignVCenter | Qt.AlignLeft, node.text)
        elif isinstance(node, ColorRect2D):
            painter.fillRect(rect, QColor(*node.color))
        elif isinstance(node, Sprite2D):
            pm = self._pixmap(node.texture_path) if node.texture_path else None
            if pm:
                painter.save()
                center = rect.center()
                painter.translate(center)
                painter.rotate(math.degrees(node.global_rotation))
                if node.flip_h or node.flip_v:
                    painter.scale(-1 if node.flip_h else 1, -1 if node.flip_v else 1)
                painter.setOpacity(max(0, min(1, node.opacity)))
                painter.drawPixmap(QRectF(-rect.width() / 2, -rect.height() / 2, rect.width(), rect.height()), pm, QRectF(pm.rect()))
                painter.restore()
            else:
                painter.setPen(QPen(QColor(225, 75, 110), 2))
                painter.drawRect(rect)
                painter.drawLine(rect.topLeft(), rect.bottomRight())
                painter.drawLine(rect.topRight(), rect.bottomLeft())
        elif isinstance(node, Label2D):
            font = painter.font()
            font.setPointSize(max(6, round(node.font_size * self.zoom)))
            painter.setFont(font)
            painter.setPen(QColor(*node.color))
            painter.drawText(rect, Qt.AlignLeft | Qt.AlignTop, node.text)
        elif isinstance(node, Camera2DNode):
            painter.setPen(QPen(QColor(245, 195, 80), 2))
            painter.drawRect(rect)
            painter.drawLine(rect.center(), rect.center() + QPointF(18, 0))
            if self.show_camera_frames:
                z = max(0.01, node.zoom)
                w = self.game_size[0] / z * self.zoom
                h = self.game_size[1] / z * self.zoom
                c = self._world_to_screen(node.global_position.x, node.global_position.y)
                painter.setPen(QPen(QColor(245, 195, 80, 150), 1, Qt.DashLine))
                painter.drawRect(QRectF(c.x() - w / 2, c.y() - h / 2, w, h))
        elif isinstance(node, TileMap2D):
            pm = self._pixmap(node.texture_path) if node.texture_path else None
            tw, th = (node.tile_size.x, node.tile_size.y)
            for x, y, tile in node.iter_tiles():
                q = self._world_to_screen(node.global_position.x + x * tw, node.global_position.y + y * th)
                dst = QRectF(q.x(), q.y(), tw * abs(node.global_scale.x) * self.zoom, th * abs(node.global_scale.y) * self.zoom)
                if pm:
                    col = tile % max(1, node.atlas_columns)
                    row = tile // max(1, node.atlas_columns)
                    src = QRectF(node.margin + col * (tw + node.spacing), node.margin + row * (th + node.spacing), tw, th)
                    painter.drawPixmap(dst, pm, src)
                else:
                    painter.fillRect(dst, QColor(75 + tile * 37 % 130, 95, 145))
                if node.debug_grid:
                    painter.setPen(QPen(QColor(85, 120, 150, 140), 1))
                    painter.drawRect(dst)
        elif isinstance(node, ParticleSystem2D):
            painter.setPen(QPen(QColor(255, 170, 75), 2))
            painter.setBrush(QColor(255, 145, 70, 80))
            painter.drawEllipse(rect.center(), 16, 16)
            for i in range(8):
                a = i * math.pi / 4
                painter.drawLine(rect.center(), rect.center() + QPointF(math.cos(a) * 28, math.sin(a) * 28))
        elif isinstance(node, Light2D):
            painter.setPen(QPen(QColor(*node.color, 170), 2))
            painter.setBrush(QColor(*node.color, 25))
            painter.drawEllipse(rect)
        elif isinstance(node, UIPanel):
            painter.fillRect(rect, QColor(*node.color))
        elif isinstance(node, UILabel):
            font = painter.font()
            font.setPointSize(max(6, round(node.font_size * self.zoom)))
            painter.setFont(font)
            painter.setPen(QColor(*node.color))
            painter.drawText(rect, Qt.AlignLeft | Qt.AlignTop, node.text)
        elif isinstance(node, Control):
            painter.setPen(QPen(QColor(120, 165, 230), 1, Qt.DashLine))
            painter.drawRect(rect)
        elif isinstance(node, Navigation2D):
            cell = node.cell_size * self.zoom
            painter.setPen(QPen(QColor(70, 155, 125, 120), 1))
            if node.debug_visible:
                origin = self._world_to_screen(node.global_position.x, node.global_position.y)
                for y in range(node.height):
                    for x in range(node.width):
                        rr = QRectF(origin.x() + x * cell, origin.y() + y * cell, cell, cell)
                        painter.drawRect(rr)
                        if node.is_blocked(x, y):
                            painter.fillRect(rr, QColor(220, 70, 90, 75))
            else:
                painter.drawRect(rect)
        elif isinstance(node, NavigationAgent2D):
            painter.setPen(QPen(QColor(80, 230, 180), 2))
            painter.drawEllipse(rect.center(), 8, 8)
        elif isinstance(node, CollisionRect2D):
            painter.setPen(QPen(QColor(80, 235, 120), 2, Qt.DashLine))
            painter.drawRect(rect)
        elif isinstance(node, PhysicsBody2D):
            if self.show_collision:
                painter.setPen(QPen(QColor(80, 190, 245), 2, Qt.DashLine))
                painter.drawRect(rect)
        else:
            painter.setPen(QPen(QColor(104, 171, 255), 2))
            painter.drawEllipse(rect.center(), 6, 6)
            painter.drawLine(rect.center().x() - 12, rect.center().y(), rect.center().x() + 12, rect.center().y())
            painter.drawLine(rect.center().x(), rect.center().y() - 12, rect.center().x(), rect.center().y() + 12)
        if node is self.selected:
            self._draw_gizmo(painter, node, rect)

    def _draw_gizmo(self, painter: QPainter, node: Node2D, rect: QRectF) -> None:
        painter.setPen(QPen(QColor(90, 190, 255), 2, Qt.DashLine))
        painter.drawRect(rect.adjusted(-3, -3, 3, 3))
        c = self._world_to_screen(node.global_position.x, node.global_position.y)
        if self.gizmo_mode == 'move':
            painter.setPen(QPen(QColor(255, 90, 90), 3))
            painter.drawLine(c, c + QPointF(55, 0))
            painter.setPen(QPen(QColor(90, 220, 120), 3))
            painter.drawLine(c, c + QPointF(0, 55))
        elif self.gizmo_mode == 'rotate':
            painter.setPen(QPen(QColor(250, 200, 80), 3))
            painter.drawEllipse(c, 34, 34)
        else:
            painter.setPen(QPen(QColor(105, 170, 255), 3))
            painter.drawRect(QRectF(c.x() + 38, c.y() - 5, 10, 10))
            painter.drawRect(QRectF(c.x() - 5, c.y() + 38, 10, 10))

    def _hit_test(self, p: QPointF) -> Node2D | None:
        if self.scene_root is None:
            return None
        candidates = [n for n in self.scene_root.walk() if isinstance(n, Node2D) and n.visible]
        candidates.sort(key=lambda n: n.z_index, reverse=True)
        for node in candidates:
            if self._node_rect(node).adjusted(-7, -7, 7, 7).contains(p):
                return node
        return None

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self._last_mouse = event.position()
        self.setFocus()
        if event.button() == Qt.MiddleButton or (event.button() == Qt.LeftButton and event.modifiers() & Qt.KeyboardModifier.AltModifier):
            self._panning = True
            return
        if event.button() == Qt.LeftButton:
            if self.tile_paint_enabled and isinstance(self.selected, TileMap2D):
                world = self._screen_to_world(event.position())
                x, y = self.selected.world_to_cell(Vector2(world.x(), world.y()))
                self.selected.set_tile(x, y, self.tile_paint_index)
                self._edit_dirty = True
                self.node_changed.emit(self.selected)
                self.update()
                return
            hit = self._hit_test(event.position())
            if hit is not None:
                self.selected = hit
                self._dragging_node = not bool(getattr(hit, 'editor_locked', False))
                self._edit_dirty = False
                self.node_selected.emit(hit)
                self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        delta = event.position() - self._last_mouse
        self._last_mouse = event.position()
        if self._panning:
            self.pan += delta
            self.update()
            return
        if self._dragging_node and isinstance(self.selected, Node2D):
            node = self.selected
            if self.gizmo_mode == 'move':
                node.position.x += delta.x() / self.zoom
                node.position.y += delta.y() / self.zoom
                if self.snap_enabled and self.snap_size > 0:
                    node.position.x = round(node.position.x / self.snap_size) * self.snap_size
                    node.position.y = round(node.position.y / self.snap_size) * self.snap_size
            elif self.gizmo_mode == 'rotate':
                node.rotation += delta.x() * 0.01
                if self.snap_enabled:
                    step = math.radians(self.rotation_snap_degrees)
                    node.rotation = round(node.rotation / step) * step
            elif self.gizmo_mode == 'scale':
                f = max(0.01, 1.0 + delta.x() * 0.01)
                node.scale.x *= f
                node.scale.y *= f
            self._edit_dirty = True
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MiddleButton or self._panning:
            self._panning = False
        if event.button() == Qt.LeftButton:
            self._dragging_node = False
            if self._edit_dirty and isinstance(self.selected, Node2D):
                self.node_changed.emit(self.selected)
            self._edit_dirty = False

    def wheelEvent(self, event: QWheelEvent) -> None:
        old = self.zoom
        factor = 1.12 if event.angleDelta().y() > 0 else 1 / 1.12
        self.zoom = min(8.0, max(0.1, self.zoom * factor))
        if abs(self.zoom - old) > 1e-06:
            self.update()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key_W:
            self.set_gizmo_mode('move')
            return
        if event.key() == Qt.Key_E:
            self.set_gizmo_mode('rotate')
            return
        if event.key() == Qt.Key_R:
            self.set_gizmo_mode('scale')
            return
        if event.key() == Qt.Key_F:
            self.frame_selected()
            return
        super().keyPressEvent(event)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls() and any((Path(u.toLocalFile()).suffix.lower() in {'.png', '.jpg', '.jpeg', '.bmp', '.webp'} for u in event.mimeData().urls())):
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        world = self._screen_to_world(event.position())
        for url in event.mimeData().urls():
            path = Path(url.toLocalFile())
            if path.suffix.lower() in {'.png', '.jpg', '.jpeg', '.bmp', '.webp'}:
                self.asset_dropped.emit(str(path), QPointF(world))
                event.acceptProposedAction()
                return
