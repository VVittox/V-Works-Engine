from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from editor.scene_document import SceneDocument
from engine import Engine
from engine.core.project_config import ProjectConfig
from engine.runtime_game import settings_from_project
from engine.scripting import attach_project_scripts

def main() -> int:
    if len(sys.argv) < 2:
        print('Usage: python editor/runner.py <scene.vscene> [project-folder]')
        return 2
    doc = SceneDocument.load(sys.argv[1])
    if len(sys.argv) >= 3 and (Path(sys.argv[2]) / 'project.vproject').exists():
        cfg = ProjectConfig.load(sys.argv[2])
        settings = settings_from_project(cfg)
        attach_project_scripts(doc.scene, cfg.root)
        settings.window.title = f'V Works — {doc.display_name}'
        engine = Engine(settings)
    else:
        engine = Engine()
        engine.settings.window.title = f'V Works — {doc.display_name}'
    engine.run(doc.scene)
    return 0
if __name__ == '__main__':
    raise SystemExit(main())
