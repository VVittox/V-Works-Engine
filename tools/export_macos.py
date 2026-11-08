




from __future__ import annotations
import importlib.util
from pathlib import Path
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from editor.build_system import _copy_project_data, safe_product_name
from engine.core.project_config import ProjectConfig


def prepare_macos_command(project_dir: str | Path, *, host_check=True):
    if host_check and sys.platform != 'darwin':
        raise RuntimeError('macOS .app must be packaged on macOS; PyInstaller cannot cross-compile a macOS binary.')
    cfg = ProjectConfig.load(project_dir)
    if not cfg.main_scene_path.exists():
        raise FileNotFoundError(f'Start scene not found: {cfg.main_scene_path}')
    cfg.ensure_build_scenes()
    if not cfg.enabled_build_scenes:
        raise ValueError('Select at least one enabled Build Scene')
    for scene in cfg.enabled_build_scenes:
        if not cfg.scene_path(scene.path).exists():
            raise FileNotFoundError(f'Build scene not found: {scene.path}')
    out = cfg.root / 'builds' / 'macos'
    work = cfg.root / '.vworks' / 'build' / 'macos'
    data = work / 'game_data'
    out.mkdir(parents=True, exist_ok=True)
    work.mkdir(parents=True, exist_ok=True)
    _copy_project_data(cfg.root, data, cfg.build.exclude)
    (data / 'build_manifest.json').write_text(json.dumps({
        'startup_scene': cfg.main_scene,
        'scenes': [{'index': i, 'path': x.path} for i,x in enumerate(cfg.enabled_build_scenes)],
    },ensure_ascii=False,indent=2),encoding='utf-8')
    entry = work / 'entry.py'
    entry.write_text('from engine.runtime_game import run_bundled_game\n'
                     'if __name__ == "__main__":\n    raise SystemExit(run_bundled_game())\n',encoding='utf-8')
    name = safe_product_name(cfg.build.product_name or cfg.name)
    cmd = [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--windowed',
           '--onedir', '--name', name, '--distpath',str(out), '--workpath',str(work/'work'),
           '--specpath',str(work/'spec'), '--paths',str(ROOT),
           '--add-data',f'{data}:game_data']
    if cfg.runtime.render_backend != 'cpu':
        for module in ('moderngl','glcontext'):
            if importlib.util.find_spec(module):
                cmd += ['--collect-all', module]
    icon = cfg.root / 'icon.icns'
    if icon.exists():
        cmd += ['--icon',str(icon)]
    cmd.append(str(entry))
    return cmd, out / f'{name}.app'


def main():
    if len(sys.argv) != 2:
        print('Usage: python tools/export_macos.py <project-folder>')
        return 2
    cmd, expected = prepare_macos_command(sys.argv[1])
    subprocess.run(cmd,check=True,cwd=ROOT)
    print('Built:', expected)
    return 0


if __name__=='__main__':
    raise SystemExit(main())
