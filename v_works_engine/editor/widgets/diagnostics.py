from __future__ import annotations
from collections import Counter
from pathlib import Path
from PySide6.QtWidgets import QPlainTextEdit

class SceneDiagnosticsWidget(QPlainTextEdit):

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setReadOnly(True)

    def refresh(self, scene, project_dir: str | Path, build_scene_count: int=0) -> None:
        nodes = list(scene.walk()) if scene is not None else []
        counts = Counter((type(n).__name__ for n in nodes))
        scripted = sum((bool(getattr(n, 'script_path', '')) for n in nodes))
        groups = sorted({g for n in nodes for g in getattr(n, 'groups', set())})
        project = Path(project_dir)
        asset_files = sum((1 for p in (project / 'assets').rglob('*') if p.is_file())) if (project / 'assets').exists() else 0
        lines = ['V WORKS SCENE DIAGNOSTICS', '=' * 28, f'Nodes: {len(nodes)}', f'Scripted nodes: {scripted}', f'Groups: {len(groups)}' + (f" ({', '.join(groups[:8])})" if groups else ''), f'Project asset files: {asset_files}', f'Enabled Build Scenes: {build_scene_count}', '', 'NODE TYPES']
        lines += [f'  {name}: {count}' for name, count in sorted(counts.items())]
        self.setPlainText('\n'.join(lines))
