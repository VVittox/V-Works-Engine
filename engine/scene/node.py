from __future__ import annotations
from typing import Iterator, List, Optional, TYPE_CHECKING
from .signals import SignalMap
from ..utils.vmath import Vector2, Vector3, Transform2D, rotate_euler, inverse_rotate_euler, direction_to_euler
if TYPE_CHECKING:
    from .scene_tree import SceneTree
_next_node_id = 0

class Node:

    def __init__(self, name: str='') -> None:
        global _next_node_id
        _next_node_id += 1
        self.name = name or self.__class__.__name__
        self.id = _next_node_id
        self.parent: Optional['Node'] = None
        self._children: List['Node'] = []
        self._in_tree = False
        self._ready_called = False
        self._process_enabled = True
        self._physics_process_enabled = True
        self._tree: Optional['SceneTree'] = None
        self.script_path: str = ''
        self.script_properties: dict = {}
        self.enabled: bool = True
        self._script_instance = None
        self.groups: set[str] = set()
        self.tag: str = 'Untagged'
        self.layer: int = 0
        self.signal_connections: list[dict[str, str]] = []
        self.editor_locked: bool = False
        self.signals = SignalMap().add('child_entered_tree', 'child_exiting_tree', 'child_removed', 'ready', 'enter_tree', 'exit_tree', 'added_to_parent', 'removed_from_parent')

    def _ready(self) -> None:
        pass

    def _process(self, delta: float) -> None:
        pass

    def _physics_process(self, delta: float) -> None:
        pass

    def _draw(self, renderer) -> None:
        pass

    def _invoke_process(self, delta: float) -> None:
        self._process(delta)
        if self._script_instance is not None:
            self._script_instance._process(delta)

    def _invoke_physics_process(self, delta: float) -> None:
        self._physics_process(delta)
        if self._script_instance is not None:
            self._script_instance._physics_process(delta)

    def _invoke_draw(self, renderer) -> None:
        self._draw(renderer)
        if self._script_instance is not None:
            self._script_instance._draw(renderer)

    def add_to_group(self, name: str) -> None:
        if str(name).strip():
            self.groups.add(str(name).strip())

    def remove_from_group(self, name: str) -> None:
        self.groups.discard(str(name))

    def is_in_group(self, name: str) -> bool:
        return str(name) in self.groups

    def get_nodes_in_group(self, name: str) -> list['Node']:
        root = self
        while root.parent is not None:
            root = root.parent
        return [n for n in root.walk() if n.is_in_group(name)]

    def has_tag(self, tag: str) -> bool:
        return self.tag == str(tag)

    def add_child(self, child: 'Node') -> 'Node':
        if not isinstance(child, Node):
            raise TypeError('child must be a Node')
        if child is self:
            raise ValueError('A node cannot be added to itself')
        cursor: Optional[Node] = self
        while cursor is not None:
            if cursor is child:
                raise ValueError('Adding this node would create a scene-tree cycle')
            cursor = cursor.parent
        if child.parent is self:
            return child
        if child.parent is not None:
            child.remove_from_parent()
        child.parent = self
        self._children.append(child)
        child.signals.emit('added_to_parent', self)
        if self._in_tree:
            child._enter_tree(self._tree)
            self.signals.emit('child_entered_tree', child)
        return child

    def insert_child(self, index: int, child: 'Node') -> 'Node':
        self.add_child(child)
        if child in self._children:
            self._children.remove(child)
            self._children.insert(max(0, min(int(index), len(self._children))), child)
        return child

    def move_child(self, child: 'Node', index: int) -> None:
        if child not in self._children:
            raise ValueError(f'{child.name} is not a child of {self.name}')
        self._children.remove(child)
        self._children.insert(max(0, min(int(index), len(self._children))), child)

    def remove_child(self, child: 'Node') -> None:
        if child not in self._children:
            raise ValueError(f'{child.name} is not a child of {self.name}')
        if child._in_tree:
            self.signals.emit('child_exiting_tree', child)
            child._exit_tree()
        self._children.remove(child)
        child.parent = None
        child.signals.emit('removed_from_parent', self)
        self.signals.emit('child_removed', child)

    def remove_from_parent(self) -> None:
        if self.parent is not None:
            self.parent.remove_child(self)

    def get_child(self, index: int) -> 'Node':
        return self._children[index]

    def get_child_count(self) -> int:
        return len(self._children)

    def get_children(self) -> List['Node']:
        return list(self._children)

    def find_child(self, name: str, recursive: bool=True) -> Optional['Node']:
        for child in self._children:
            if child.name == name:
                return child
            if recursive:
                found = child.find_child(name, True)
                if found is not None:
                    return found
        return None

    def get_node(self, path: str) -> Optional['Node']:
        if not path or path == '.':
            return self
        current: Optional[Node]
        if path.startswith('/'):
            current = self
            while current.parent is not None:
                current = current.parent
            parts = path.strip('/').split('/')
            if parts and parts[0] == current.name:
                parts = parts[1:]
        else:
            current = self
            parts = path.split('/')
        for part in parts:
            if part in ('', '.'):
                continue
            if part == '..':
                current = current.parent if current is not None else None
                continue
            if current is None:
                return None
            current = next((c for c in current._children if c.name == part), None)
            if current is None:
                return None
        return current

    def walk(self, include_self: bool=True) -> Iterator['Node']:
        if include_self:
            yield self
        for child in tuple(self._children):
            yield from child.walk(True)

    def _enter_tree(self, tree: Optional['SceneTree']) -> None:
        if self._in_tree:
            return
        self._tree = tree
        self._in_tree = True
        self.signals.emit('enter_tree')
        for child in tuple(self._children):
            child._enter_tree(tree)
        if not self._ready_called:
            self._ready_called = True
            self._ready()
            if self._script_instance is not None:
                self._script_instance._ready()
            self.signals.emit('ready')

    def _exit_tree(self) -> None:
        if not self._in_tree:
            return
        before = getattr(self._script_instance, '_before_exit_tree', None)
        if callable(before):
            before()
        for child in reversed(tuple(self._children)):
            child._exit_tree()
        callback = getattr(self._script_instance, '_exit_tree', None)
        if callable(callback):
            callback()
        self.signals.emit('exit_tree')
        self._in_tree = False
        self._tree = None

    def get_tree(self) -> Optional['SceneTree']:
        return self._tree

    @property
    def is_enabled_in_tree(self) -> bool:
        node = self
        while node is not None:
            if not node.enabled:
                return False
            node = node.parent
        return True

    @property
    def is_visible_in_tree(self) -> bool:
        node = self
        while node is not None:
            if not node.enabled or not getattr(node, 'visible', True):
                return False
            node = node.parent
        return True

    @property
    def is_inside_tree(self) -> bool:
        return self._in_tree

    def set_process(self, enabled: bool) -> None:
        self._process_enabled = bool(enabled)

    def set_physics_process(self, enabled: bool) -> None:
        self._physics_process_enabled = bool(enabled)

    def queue_free(self) -> None:
        if self._tree is not None:
            self._tree.queue_free(self)
        else:
            self.remove_from_parent()

    def _path(self) -> str:
        parts = [self.name]
        parent = self.parent
        while parent is not None:
            parts.append(parent.name)
            parent = parent.parent
        return '/' + '/'.join(reversed(parts))

    @property
    def path(self) -> str:
        return self._path()

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__} name={self.name!r} id={self.id} path={self.path!r}>'

class Node2D(Node):

    def __init__(self, name: str='') -> None:
        super().__init__(name)
        self.position = Vector2()
        self.rotation = 0.0
        self.scale = Vector2(1.0, 1.0)
        self.visible = True
        self.z_index = 0
        self.material_path = ''

    @property
    def transform(self) -> Transform2D:
        return Transform2D(self.position, self.rotation, self.scale)

    @property
    def global_rotation(self) -> float:
        value = float(self.rotation)
        parent = self.parent
        while parent is not None:
            if isinstance(parent, Node2D):
                value += parent.rotation
            parent = parent.parent
        return value

    @property
    def global_scale(self) -> Vector2:
        value = Vector2(self.scale.x, self.scale.y)
        parent = self.parent
        while parent is not None:
            if isinstance(parent, Node2D):
                value = value * parent.scale
            parent = parent.parent
        return value

    @property
    def global_position(self) -> Vector2:
        p = Vector2(self.position.x, self.position.y)
        parent = self.parent
        while parent is not None:
            if isinstance(parent, Node2D):
                p = parent.transform.transform_point(p)
            parent = parent.parent
        return p


class Node3D(Node):

    def __init__(self, name: str='') -> None:
        super().__init__(name)
        self.position = Vector3()
        self.rotation = Vector3()
        self.scale = Vector3(1.0, 1.0, 1.0)
        self.visible = True
        self.render_layer = 0
        self.material_path = ''

    @property
    def global_rotation(self) -> Vector3:
        value = Vector3(self.rotation.x, self.rotation.y, self.rotation.z)
        parent = self.parent
        while parent is not None:
            if isinstance(parent, Node3D):
                value = value + parent.rotation
            parent = parent.parent
        return value

    @property
    def global_scale(self) -> Vector3:
        value = Vector3(self.scale.x, self.scale.y, self.scale.z)
        parent = self.parent
        while parent is not None:
            if isinstance(parent, Node3D):
                value = Vector3(value.x * parent.scale.x, value.y * parent.scale.y, value.z * parent.scale.z)
            parent = parent.parent
        return value

    @property
    def global_position(self) -> Vector3:
        return self.to_global(Vector3())

    def transform_point(self, point: Vector3) -> Vector3:
        scaled = Vector3(point.x * self.scale.x, point.y * self.scale.y, point.z * self.scale.z)
        return rotate_euler(scaled, self.rotation) + self.position

    def inverse_transform_point(self, point: Vector3) -> Vector3:
        value = inverse_rotate_euler(point - self.position, self.rotation)
        return Vector3(
            value.x / self.scale.x if not abs(self.scale.x) < 1e-12 else 0.0,
            value.y / self.scale.y if not abs(self.scale.y) < 1e-12 else 0.0,
            value.z / self.scale.z if not abs(self.scale.z) < 1e-12 else 0.0,
        )

    def to_global(self, point: Vector3) -> Vector3:
        value = self.transform_point(point)
        parent = self.parent
        while parent is not None:
            if isinstance(parent, Node3D):
                value = parent.transform_point(value)
            parent = parent.parent
        return value

    def to_local(self, point: Vector3) -> Vector3:
        chain = []
        node = self
        while node is not None:
            if isinstance(node, Node3D):
                chain.append(node)
            node = node.parent
        value = Vector3(point.x, point.y, point.z)
        for item in reversed(chain):
            value = item.inverse_transform_point(value)
        return value

    @property
    def global_right(self) -> Vector3:
        origin = self.global_position
        return (self.to_global(Vector3.RIGHT()) - origin).normalized

    @property
    def global_up(self) -> Vector3:
        origin = self.global_position
        return (self.to_global(Vector3.UP()) - origin).normalized

    @property
    def global_forward(self) -> Vector3:
        origin = self.global_position
        return (self.to_global(Vector3.FORWARD()) - origin).normalized

    def translate(self, offset: Vector3) -> None:
        self.position = self.position + offset

    def rotate_x(self, angle: float) -> None:
        self.rotation.x += float(angle)

    def rotate_y(self, angle: float) -> None:
        self.rotation.y += float(angle)

    def rotate_z(self, angle: float) -> None:
        self.rotation.z += float(angle)

    def look_at(self, target: Vector3) -> None:
        target_local = target
        if isinstance(self.parent, Node3D):
            target_local = self.parent.to_local(target)
        direction = target_local - self.position
        if direction.length:
            self.rotation = direction_to_euler(direction)
