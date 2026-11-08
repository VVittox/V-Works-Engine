from __future__ import annotations
import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any
_module_cache = {}

class VScript:

    def __init__(self, owner) -> None:
        self.owner = owner

    @property
    def tree(self):
        return self.owner.get_tree()

    @property
    def engine(self):
        return self.tree.engine if self.tree else None

    @property
    def input(self):
        return self.engine.input if self.engine else None

    @property
    def assets(self):
        return self.engine.assets if self.engine else None

    def _ready(self) -> None:
        pass

    def _process(self, delta: float) -> None:
        pass

    def _physics_process(self, delta: float) -> None:
        pass

    def _draw(self, renderer) -> None:
        pass

    def _exit_tree(self) -> None:
        pass

    @property
    def properties(self) -> dict:

        return self.owner.script_properties

def _load_module(path: Path) -> ModuleType:
    stat=path.stat();key=(str(path.resolve()),stat.st_mtime_ns,stat.st_size)
    if key in _module_cache:
        return _module_cache[key]
    module_name = f'vworks_user_{abs(hash(str(path.resolve())))}'
    spec = importlib.util.spec_from_file_location(module_name, str(path))
    if spec is None or spec.loader is None:
        raise ImportError(f'Could not load script: {path}')
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    if len(_module_cache)>=256:_module_cache.pop(next(iter(_module_cache)))
    _module_cache[key]=module
    return module

def attach_script_to_node(node, project_root: str | Path, *, strict: bool=False):
    script_path = str(getattr(node, 'script_path', '') or '').strip()
    if not script_path:
        node._script_instance = None
        return None
    path = Path(script_path)
    if not path.is_absolute():
        path = Path(project_root) / path
    path = path.resolve()
    if not path.exists():
        if strict:
            raise FileNotFoundError(f'Script not found: {path}')
        print(f'[VScript] Missing script: {path}')
        return None
    try:
        root = str(Path(project_root).resolve())
        if root not in sys.path:
            sys.path.insert(0, root)
        module = _load_module(path)
        cls = getattr(module, 'Script', None)
        if cls is None:
            raise AttributeError('Script file must define class Script')
        instance = cls(node)
        node._script_instance = instance
        return instance
    except Exception as exc:
        if strict:
            raise
        print(f'[VScript] Failed to attach {path}: {exc}')
        node._script_instance = None
        return None

def attach_project_scripts(root, project_root: str | Path, *, strict: bool=False) -> int:
    count = 0
    for node in root.walk():
        if getattr(node, 'script_path', ''):
            if attach_script_to_node(node, project_root, strict=strict) is not None:
                count += 1
    return count

def connect_scene_signals(root, *, strict: bool=False) -> int:
    count = 0
    for source in root.walk():
        for conn in getattr(source, 'signal_connections', []):
            try:
                signal_name = str(conn.get('signal', '')).strip()
                target_path = str(conn.get('target', '')).strip()
                method_name = str(conn.get('method', '')).strip()
                if not signal_name or not target_path or (not method_name):
                    continue
                target = root.get_node(target_path)
                if target is None and (not target_path.startswith('/')):
                    target = source.get_node(target_path)
                if target is None:
                    raise LookupError(f'Signal target not found: {target_path}')
                script = getattr(target, '_script_instance', None)
                handler = getattr(script, method_name, None) if script is not None else None
                if handler is None:
                    handler = getattr(target, method_name, None)
                if not callable(handler):
                    raise AttributeError(f'Signal target method not found: {target_path}.{method_name}')
                source.signals.connect(signal_name, handler)
                count += 1
            except Exception as exc:
                if strict:
                    raise
                print(f'[VSignal] Connection failed on {source.path}: {exc}')
    return count
