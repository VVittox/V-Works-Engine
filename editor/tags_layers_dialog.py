from __future__ import annotations
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QLabel, QLineEdit, QListWidget, QTabWidget, QVBoxLayout, QWidget

class TagsLayersDialog(QDialog):

    def __init__(self, project, scene, parent=None):
        super().__init__(parent)
        self.project = project
        self.scene = scene
        self.setWindowTitle('Tags, Layers & Groups')
        self.resize(640, 560)
        outer = QVBoxLayout(self)
        tabs = QTabWidget()
        outer.addWidget(tabs, 1)
        tags = QWidget()
        tl = QVBoxLayout(tags)
        self.tag_list = QListWidget()
        self.tag_list.addItems(project.tags)
        tl.addWidget(QLabel('One tag per line. Tags are Unity-style single labels on nodes.'))
        tl.addWidget(self.tag_list)
        tabs.addTab(tags, 'Tags')
        layers = QWidget()
        lf = QFormLayout(layers)
        self.layer_edits = []
        values = (project.layers + [f'Layer {i}' for i in range(32)])[:32]
        for i, name in enumerate(values):
            e = QLineEdit(name)
            self.layer_edits.append(e)
            lf.addRow(f'{i}', e)
        tabs.addTab(layers, 'Layers')
        groups = QWidget()
        gl = QVBoxLayout(groups)
        self.groups = QListWidget()
        all_groups = sorted({g for n in scene.walk() for g in getattr(n, 'groups', set())})
        self.groups.addItems(all_groups)
        gl.addWidget(QLabel('Godot-style groups currently used by nodes in this scene.'))
        gl.addWidget(self.groups)
        tabs.addTab(groups, 'Groups')
        buttons = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Save)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)

    def _save(self):
        self.project.tags = [self.tag_list.item(i).text().strip() for i in range(self.tag_list.count()) if self.tag_list.item(i).text().strip()]
        if 'Untagged' not in self.project.tags:
            self.project.tags.insert(0, 'Untagged')
        self.project.layers = [e.text().strip() or f'Layer {i}' for i, e in enumerate(self.layer_edits)]
        self.project.save()
        self.accept()
