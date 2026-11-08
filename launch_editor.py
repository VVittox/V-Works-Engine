from __future__ import annotations
import json
import sys
from pathlib import Path


def _adjacent_game_boot() -> Path | None:
    if not getattr(sys, 'frozen', False):
        return None
    marker = Path(sys.executable).resolve().parent / 'vworks_game_boot.json'
    return marker if marker.exists() else None


def _run_adjacent_game(marker: Path) -> int:
    payload = json.loads(marker.read_text(encoding='utf-8'))
    game_data = str(payload.get('game_data', 'game_data'))
    project = marker.parent / game_data
    from engine.runtime_game import run_project
    return run_project(project)


def main() -> int:
    marker = _adjacent_game_boot()
    if marker is not None:
        return _run_adjacent_game(marker)
    if len(sys.argv) >= 2 and sys.argv[1] == '--vworks-export-game':
        if len(sys.argv) < 5:
            print('Usage: --vworks-export-game <stage> <output> <name>')
            return 2
        from editor.build_system import export_game_from_frozen_editor
        export_game_from_frozen_editor(sys.argv[2], sys.argv[3], sys.argv[4])
        return 0
    if len(sys.argv) >= 3 and sys.argv[1] == '--run-project':
        from engine.runtime_game import run_project
        return run_project(sys.argv[2])
    if len(sys.argv) >= 4 and sys.argv[1] == '--run-scene':
        from editor.runner import main as runner_main
        sys.argv = [sys.argv[0], sys.argv[2], sys.argv[3]]
        return runner_main()
    from editor.app import main as editor_main
    return editor_main()


if __name__ == '__main__':
    raise SystemExit(main())
