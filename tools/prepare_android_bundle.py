



from __future__ import annotations
import json
from pathlib import Path
import sys
import zipfile
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from engine.core.project_config import ProjectConfig

SKIP_DIRS = {'.venv','.vworks','.git','.idea','.vscode','builds','__pycache__','validation'}


def prepare_bundle(project_root: str | Path, output: str | Path | None=None) -> Path:
    cfg = ProjectConfig.load(project_root)
    if not cfg.main_scene_path.exists():
        raise FileNotFoundError('Cannot stage Android port without the startup scene')
    if not (ROOT/'engine/runtime_game.py').exists():
        raise RuntimeError('Android staging requires the engine source checkout, not a frozen editor executable.')
    target = Path(output or (cfg.root/'builds/android_stage/android_source_bundle.zip')).resolve()
    target.parent.mkdir(parents=True,exist_ok=True)
    sources = ((ROOT/'engine','engine'),(cfg.root,'game_data'))
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as bundle:
        for folder,prefix in sources:
            for path in folder.rglob('*'):
                if not path.is_file() or path.is_symlink() or any(part in SKIP_DIRS for part in path.relative_to(folder).parts) or path.suffix in ('.pyc','.pyo'):
                    continue
                if path.resolve() == target:
                    continue
                bundle.write(path, f'{prefix}/{path.relative_to(folder).as_posix()}')
        bundle.writestr('ANDROID_STATUS.json',json.dumps({
            'status':'source_staging_only_not_apk',
            'startup_scene':cfg.main_scene,
            'requires':'Android runtime using SDL2 / OpenGL ES and a supported Python-for-Android toolchain',
            'limitations':['Desktop PySide6 editor not bundled','Desktop ModernGL context not portable to Android GLES','Input/touch, lifecycle and audio require Android integration'],
        },ensure_ascii=False,indent=2))
    return target


if __name__=='__main__':
    if len(sys.argv)!=2:
        raise SystemExit('Usage: python tools/prepare_android_bundle.py <project-folder>')
    print('Android port source staging (NOT APK):',prepare_bundle(sys.argv[1]))
