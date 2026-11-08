from pathlib import Path
from PyInstaller.utils.hooks import collect_all
import importlib.util


datas = [('editor/resources', 'editor/resources')]
binaries = []
hiddenimports = []

for package in ('PySide6', 'pygame', 'moderngl', 'glcontext'):
    if importlib.util.find_spec(package) is not None:
        package_data, package_binaries, package_imports = collect_all(package)
        datas.extend(package_data)
        binaries.extend(package_binaries)
        hiddenimports.extend(package_imports)

analysis = Analysis(
    ['launch_editor.py'],
    pathex=[str(Path.cwd())],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

archive = PYZ(analysis.pure)

exe = EXE(
    archive,
    analysis.scripts,
    analysis.binaries,
    analysis.datas,
    [],
    name='V Works Engine',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    icon='editor/resources/vworks_icon.ico',
)
