from __future__ import annotations
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QDropEvent
from PySide6.QtWidgets import QAbstractItemView, QTreeWidget, QTreeWidgetItem
from engine.scene import Node

class SceneTreeWidget(QTreeWidget):
    node_selected = Signal(object)
    hierarchy_changed = Signal(object)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setHeaderLabel('Scene')
        self.setIndentation(16)
        self.setAnimated(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setDropIndicatorShown(True)
        self.itemSelectionChanged.connect(self._emit_selection)
        self._root_node = None
        self._search_query = ''

    def set_scene(self, root: Node) -> None:
        self._root_node = root
        self.refresh()

    def refresh(self, selected: Node | None=None) -> None:
        expanded = self._expanded_paths()
        self.clear()
        if self._root_node is None:
            return
        root_item = self._make_item(self._root_node, True)
        self.addTopLevelItem(root_item)
        self._add_children(root_item, self._root_node)
        root_item.setExpanded(True)
        self._restore_expanded(expanded)
        self._apply_filter()
        if selected is not None:
            self.select_node(selected)

    def filter_nodes(self, text: str) -> None:
        self._search_query = text.casefold().strip()
        self._apply_filter()

    def _apply_filter(self) -> None:
        needle = self._search_query
        def visit(item: QTreeWidgetItem, parent_match: bool=False) -> bool:
            match = parent_match or needle in item.text(0).casefold()
            child_match = False
            for i in range(item.childCount()):
                child_match = visit(item.child(i), match) or child_match
            visible = match or child_match
            item.setHidden(not visible)
            if needle and child_match:
                item.setExpanded(True)
            return visible
        for i in range(self.topLevelItemCount()):
            visit(self.topLevelItem(i))

    def _make_item(self, node: Node, is_root=False) -> QTreeWidgetItem:
        item = QTreeWidgetItem([f'{node.name}  [{node.__class__.__name__}]'])
        item.setData(0, Qt.UserRole, node)
        flags = item.flags() | Qt.ItemIsDropEnabled
        if not is_root:
            flags |= Qt.ItemIsDragEnabled
        else:
            flags &= ~Qt.ItemIsDragEnabled
        item.setFlags(flags)
        return item

    def _add_children(self, parent_item: QTreeWidgetItem, node: Node) -> None:
        for child in node.get_children():
            item = self._make_item(child)
            parent_item.addChild(item)
            self._add_children(item, child)

    def select_node(self, node: Node) -> None:
        stack = [self.topLevelItem(i) for i in range(self.topLevelItemCount())]
        while stack:
            item = stack.pop()
            if item.data(0, Qt.UserRole) is node:
                self.setCurrentItem(item)
                return
            stack.extend((item.child(i) for i in range(item.childCount())))

    def current_node(self) -> Node | None:
        item = self.currentItem()
        return item.data(0, Qt.UserRole) if item else None

    def _emit_selection(self) -> None:
        node = self.current_node()
        if node is not None:
            self.node_selected.emit(node)

    def dropEvent(self, event: QDropEvent) -> None:
        item = self.currentItem()
        node = item.data(0, Qt.UserRole) if item else None
        if node is None or node is self._root_node:
            event.ignore()
            return
        super().dropEvent(event)
        item = self.currentItem()
        parent_item = item.parent() if item else None
        if item is None or parent_item is None:
            self.refresh(node)
            return
        new_parent = parent_item.data(0, Qt.UserRole)
        try:
            new_parent.insert_child(parent_item.indexOfChild(item), node)
            self.hierarchy_changed.emit(node)
            self.refresh(node)
        except Exception:
            self.refresh(node)

    def _expanded_paths(self) -> set[str]:
        result = set()
        stack = [self.topLevelItem(i) for i in range(self.topLevelItemCount())]
        while stack:
            item = stack.pop()
            node = item.data(0, Qt.UserRole)
            if item.isExpanded() and node is not None:
                result.add(node.path)
            stack.extend((item.child(i) for i in range(item.childCount())))
        return result

    def _restore_expanded(self, paths: set[str]) -> None:
        stack = [self.topLevelItem(i) for i in range(self.topLevelItemCount())]
        while stack:
            item = stack.pop()
            node = item.data(0, Qt.UserRole)
            if node is not None and node.path in paths:
                item.setExpanded(True)
            stack.extend((item.child(i) for i in range(item.childCount())))
