from __future__ import annotations
import os
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from engine.core.project_config import ProjectConfig

@dataclass
class BuildPlan:
    command: list[str]
    output_dir: Path
    cache_dir: Path
    stage_dir: Path
    entry_script: Path
    executable_name: str
    backend: str = 'pyinstaller'


def safe_product_name(name: str) -> str:
    name = re.sub('[<>:"/\\\\|?*]+', '_', name).strip().strip('.')
    return name or 'VWorksGame'


def _copy_project_data(project_root: Path, stage: Path) -> None:
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True, exist_ok=True)
    excluded = {'.venv', '.git', '.idea', '.vscode', '.vworks', 'builds', '__pycache__'}
    for item in project_root.iterdir():
        if item.name in excluded:
            continue
        dst = stage / item.name
        if item.is_dir():
            shutil.copytree(item, dst, ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '*.pyo', '.DS_Store'))
        elif item.is_file():
            shutil.copy2(item, dst)


def _version_tuple(version: str) -> tuple[int, int, int, int]:
    nums = [int(x) for x in re.findall('\\d+', version)[:4]]
    nums += [0] * (4 - len(nums))
    return tuple(nums[:4])


def _write_version_file(path: Path, cfg: ProjectConfig, product_name: str) -> None:
    v = _version_tuple(cfg.build.version)
    company = cfg.build.company.replace("'", '')
    product = product_name.replace("'", '')
    version = cfg.build.version.replace("'", '')
    path.write_text(f"# UTF-8\nVSVersionInfo(\n  ffi=FixedFileInfo(filevers={v}, prodvers={v}, mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),\n  kids=[\n    StringFileInfo([StringTable('040904B0', [\n      StringStruct('CompanyName', '{company}'),\n      StringStruct('FileDescription', '{product}'),\n      StringStruct('FileVersion', '{version}'),\n      StringStruct('InternalName', '{product}'),\n      StringStruct('OriginalFilename', '{product}.exe'),\n      StringStruct('ProductName', '{product}'),\n      StringStruct('ProductVersion', '{version}')\n    ])]),\n    VarFileInfo([VarStruct('Translation', [1033, 1200])])\n  ]\n)\n", encoding='utf-8')


def is_frozen_editor() -> bool:
    return bool(getattr(sys, 'frozen', False))


def prepare_windows_build(cfg: ProjectConfig, engine_source_root: str | Path, output_dir: str | Path | None=None, onefile: bool | None=None, default_icon: str | Path | None=None) -> BuildPlan:
    if not cfg.main_scene_path.exists():
        raise FileNotFoundError(f'Main scene not found: {cfg.main_scene_path}')
    cfg.ensure_build_scenes()
    if not cfg.enabled_build_scenes:
        raise ValueError('No enabled Build Scenes. Open Build > Build Scenes and enable at least one scene.')
    for scene in cfg.enabled_build_scenes:
        scene_path = cfg.scene_path(scene.path)
        if not scene_path.exists():
            raise FileNotFoundError(f'Build scene not found: {scene.path}')
    try:
        cfg.main_scene_path.relative_to(cfg.root)
    except ValueError as exc:
        raise ValueError('The main scene must be inside the project folder before exporting.') from exc
    engine_source_root = Path(engine_source_root).resolve()
    output = Path(output_dir or cfg.root / 'builds' / 'windows').resolve()
    output.mkdir(parents=True, exist_ok=True)
    cache = cfg.root / '.vworks' / 'build' / 'windows'
    stage = cache / 'game_data'
    cache.mkdir(parents=True, exist_ok=True)
    _copy_project_data(cfg.root, stage)
    manifest = stage / 'build_manifest.json'
    import json
    manifest.write_text(json.dumps({'startup_scene': cfg.main_scene, 'scenes': [{'index': i, 'path': scene.path} for i, scene in enumerate(cfg.enabled_build_scenes)]}, ensure_ascii=False, indent=2), encoding='utf-8')
    name = safe_product_name(cfg.build.product_name or cfg.name)
    if is_frozen_editor():
        command = [sys.executable, '--vworks-export-game', str(stage), str(output), name]
        return BuildPlan(command, output, cache, stage, Path(sys.executable), name, 'frozen-runtime-copy')
    entry = cache / 'vworks_export_entry.py'
    entry.write_text("from engine.runtime_game import run_bundled_game\nif __name__ == '__main__':\n    raise SystemExit(run_bundled_game())\n", encoding='utf-8')
    version_file = cache / 'version_info.txt'
    _write_version_file(version_file, cfg, name)
    use_onefile = cfg.build.onefile if onefile is None else bool(onefile)
    work = cache / 'work'
    spec = cache / 'spec'
    work.mkdir(parents=True, exist_ok=True)
    spec.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, '-m', 'PyInstaller', '--noconfirm']
    if cfg.build.clean_build:
        command.append('--clean')
    command += ['--console' if cfg.build.debug_console else '--windowed', '--onefile' if use_onefile else '--onedir', '--name', name, '--distpath', str(output), '--workpath', str(work), '--specpath', str(spec), '--paths', str(engine_source_root), '--version-file', str(version_file), '--add-data', f'{stage}{os.pathsep}game_data']
    icon_candidates = [cfg.root / 'icon.ico', cfg.icon_path if cfg.icon_path.suffix.lower() == '.ico' else None, Path(default_icon).resolve() if default_icon else None]
    icon = next((p for p in icon_candidates if p is not None and p.exists()), None)
    if icon is not None:
        command += ['--icon', str(icon)]
    command.append(str(entry))
    return BuildPlan(command, output, cache, stage, entry, name, 'pyinstaller')


def export_game_from_frozen_editor(stage_dir: str | Path, output_dir: str | Path, executable_name: str) -> Path:
    if not is_frozen_editor():
        raise RuntimeError('Frozen runtime copy export is only available from a packaged V Works Engine editor.')
    stage = Path(stage_dir).resolve()
    output = Path(output_dir).resolve()
    name = safe_product_name(executable_name)
    if not (stage / 'project.vproject').exists():
        raise FileNotFoundError(f'Export stage has no project.vproject: {stage}')
    source_exe = Path(sys.executable).resolve()
    source_dir = source_exe.parent
    target_dir = output / name
    if target_dir.exists():
        shutil.rmtree(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    if hasattr(sys, '_MEIPASS') and (source_dir / '_internal').exists():
        for item in source_dir.iterdir():
            if item.resolve() == source_exe:
                continue
            dst = target_dir / item.name
            if item.is_dir():
                shutil.copytree(item, dst)
            else:
                shutil.copy2(item, dst)
    target_exe = target_dir / f'{name}.exe'
    shutil.copy2(source_exe, target_exe)
    shutil.copytree(stage, target_dir / 'game_data')
    import json
    (target_dir / 'vworks_game_boot.json').write_text(json.dumps({'format': 'vworks_game_boot', 'version': 1, 'game_data': 'game_data'}, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'V Works frozen export complete: {target_exe}')
    print('Backend: frozen editor runtime copy')
    return target_exe


def assert_windows_build_host() -> None:
    if sys.platform != 'win32':
        raise RuntimeError('Windows .exe export must be run on Windows. PyInstaller does not cross-compile Windows executables.')
