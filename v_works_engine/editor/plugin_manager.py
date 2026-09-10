from __future__ import annotations
import importlib.util, json, shutil, sys, zipfile
from dataclasses import dataclass
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFileDialog, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QMessageBox, QPushButton, QVBoxLayout

@dataclass
class PluginInfo:
    id: str
    name: str
    version: str
    entry: str
    root: Path
    description: str = ''

class PluginHost:

    def __init__(self, project_dir, enabled=None):
        self.project_dir = Path(project_dir).resolve()
        self.enabled = set(enabled or [])
        self.loaded = {}

    def scan(self):
        out = []
        addons = self.project_dir / 'addons'
        if not addons.exists():
            return out
        for manifest in addons.glob('*/plugin.json'):
            try:
                d = json.loads(manifest.read_text(encoding='utf-8'))
                pid = str(d.get('id') or manifest.parent.name)
                out.append(PluginInfo(pid, str(d.get('name', pid)), str(d.get('version', '0.1.0')), str(d.get('entry', 'plugin.py')), manifest.parent, str(d.get('description', ''))))
            except Exception:
                continue
        return out

    def load_enabled(self, editor):
        for info in self.scan():
            if info.id not in self.enabled or info.id in self.loaded:
                continue
            path = (info.root / info.entry).resolve()
            try:
                spec = importlib.util.spec_from_file_location(f"vworks_plugin_{info.id.replace('.', '_')}", path)
                if not spec or not spec.loader:
                    raise ImportError(path)
                mod = importlib.util.module_from_spec(spec)
                sys.modules[spec.name] = mod
                spec.loader.exec_module(mod)
                if hasattr(mod, 'register'):
                    mod.register(editor)
                self.loaded[info.id] = mod
                if hasattr(editor, 'log'):
                    editor.log(f'Plugin loaded: {info.name} {info.version}')
            except Exception as exc:
                if hasattr(editor, 'log'):
                    editor.log(f'Plugin failed: {info.name}: {exc}')

    def shutdown(self, editor):
        for pid, mod in list(self.loaded.items()):
            try:
                if hasattr(mod, 'unregister'):
                    mod.unregister(editor)
            except Exception:
                pass
        self.loaded.clear()

class PluginManagerDialog(QDialog):

    def __init__(self, project, parent=None):
        super().__init__(parent)
        self.project = project
        self.host = PluginHost(project.root, project.enabled_plugins)
        self.setWindowTitle('Package / Plugin Manager')
        self.resize(760, 540)
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel('Plugins live in addons/<plugin>/plugin.json. Enabled plugins execute local Python code in the editor.'))
        row = QHBoxLayout()
        install = QPushButton('Install ZIP…')
        install.clicked.connect(self._install)
        sample = QPushButton('Create Sample Plugin')
        sample.clicked.connect(self._sample)
        row.addWidget(install)
        row.addWidget(sample)
        row.addStretch()
        lay.addLayout(row)
        self.list = QListWidget()
        lay.addWidget(self.list, 1)
        self._refresh()
        buttons = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Save)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        lay.addWidget(buttons)

    def _refresh(self):
        self.list.clear()
        for info in self.host.scan():
            item = QListWidgetItem(f'{info.name}  {info.version}\n{info.id} — {info.description}')
            item.setData(Qt.UserRole, info.id)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if info.id in self.project.enabled_plugins else Qt.Unchecked)
            self.list.addItem(item)

    def _install(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Install V Works Plugin ZIP', str(Path.home()), 'ZIP (*.zip)')
        if not path:
            return
        target = self.project.root / 'addons'
        target.mkdir(exist_ok=True)
        try:
            with zipfile.ZipFile(path) as z:
                for member in z.infolist():
                    dest = (target / member.filename).resolve()
                    try:
                        dest.relative_to(target.resolve())
                    except ValueError:
                        raise ValueError('Unsafe path in plugin ZIP')
                z.extractall(target)
            self._refresh()
        except Exception as exc:
            QMessageBox.critical(self, 'Install Plugin', str(exc))

    def _sample(self):
        root = self.project.root / 'addons' / 'hello_vworks'
        root.mkdir(parents=True, exist_ok=True)
        (root / 'plugin.json').write_text(json.dumps({'id': 'hello_vworks', 'name': 'Hello V Works', 'version': '1.0.0', 'entry': 'plugin.py', 'description': 'Example editor plugin'}, indent=2), encoding='utf-8')
        (root / 'plugin.py').write_text('def register(editor):\n    editor.log("Hello from V Works plugin!")\n\ndef unregister(editor):\n    pass\n', encoding='utf-8')
        self._refresh()

    def _save(self):
        self.project.enabled_plugins = [self.list.item(i).data(Qt.UserRole) for i in range(self.list.count()) if self.list.item(i).checkState() == Qt.Checked]
        self.project.save()
        self.accept()
