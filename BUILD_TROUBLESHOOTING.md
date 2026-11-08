# V Works Engine — Windows build troubleshooting

## Editor built with PyInstaller, but game export fails

Older V Works Engine builds used `sys.executable -m PyInstaller` from the editor. After freezing the editor, `sys.executable` is the editor executable rather than Python. This version detects that state and uses the packaged runtime export backend instead.

Rebuild the editor from the current source before testing the fix.

## Source editor build

Install dependencies into the project virtual environment:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Run the editor from source and use **Build > Build Windows**. This path can create normal PyInstaller `onedir` or `onefile` game builds.

## Packaged editor build

Open the rebuilt `V Works Engine.exe`, open a project and use **Build > Build Windows**.

The packaged editor exports a portable game directory. The game executable must stay next to its `_internal` directory and `game_data` directory.

Do not copy only the `.exe` out of an `onedir` build.

## Build scenes

At least one scene must be enabled in **Build Scenes**. All enabled scene files must exist inside the project. The project's Main Scene must also exist inside the project directory.

## Debugging a game

Temporarily enable **Debug Console** in Project Settings before building. If the game exits immediately, launch its `.exe` from PowerShell so Python/runtime errors remain visible.
