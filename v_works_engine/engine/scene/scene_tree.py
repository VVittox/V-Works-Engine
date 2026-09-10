from __future__ import annotations
from typing import List, Optional
from .node import Node, Node2D, Node3D
from .scene import Scene

class SceneTree:

    def __init__(self, engine=None) -> None:
        self.engine = engine
        self.root = Node('Root')
        self.current_scene: Optional[Scene] = None
        self._delete_queue: List[Node] = []
        self.root._enter_tree(self)

    def set_current_scene(self, scene: Scene) -> Scene:
        if self.current_scene is scene:
            return scene
        if self.current_scene is not None and self.current_scene.parent is self.root:
            self.root.remove_child(self.current_scene)
        self.current_scene = scene
        self.root.add_child(scene)
        return scene

    def get_nodes_in_group(self, name: str):
        return [node for node in self.root.walk() if node.is_in_group(name)]

    def queue_free(self, node: Node) -> None:
        if node is self.root:
            raise ValueError('SceneTree root cannot be freed')
        if node not in self._delete_queue:
            self._delete_queue.append(node)

    def _flush_delete_queue(self) -> None:
        queue, self._delete_queue = (self._delete_queue, [])
        for node in queue:
            if node.parent is not None:
                node.parent.remove_child(node)
            if node is self.current_scene:
                self.current_scene = None

    def physics_process(self, delta: float) -> None:
        for node in tuple(self.root.walk()):
            if node._in_tree and node._physics_process_enabled:
                node._invoke_physics_process(delta)
        self._flush_delete_queue()

    def process(self, delta: float) -> None:
        for node in tuple(self.root.walk()):
            if node._in_tree and node._process_enabled:
                node._invoke_process(delta)
        self._flush_delete_queue()

    def draw(self, renderer) -> None:
        if hasattr(renderer, 'prepare_scene_3d'):
            renderer.prepare_scene_3d(self.root)

        def draw_branch(node: Node, want_3d: bool) -> None:
            if not getattr(node, 'visible', True):
                return
            is_3d = isinstance(node, Node3D)
            if is_3d == want_3d:
                node._invoke_draw(renderer)
            children = node.get_children()
            children.sort(key=lambda n: getattr(n, 'z_index', getattr(n, 'render_layer', 0)))
            for child in children:
                draw_branch(child, want_3d)
        draw_branch(self.root, True)
        if hasattr(renderer, 'flush_3d'):
            renderer.flush_3d()
        draw_branch(self.root, False)
