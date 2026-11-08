# Установка и быстрый старт

## Требования

- Python 3.12 (рекомендуется для Windows-сборки; другая поддерживаемая версия Python 3 может работать, но требует тестов).
- `pygame>=2.5.2,<3`, `PySide6>=6.7,<7`, `PyInstaller>=6.6,<7` из `requirements.txt`.
- Для режима GPU: ModernGL и glcontext из `requirements-gpu.txt`, графический драйвер и OpenGL 3.3.
- Для компиляции Windows EXE требуется **Windows**; для `.app` — **macOS**.

## Установка Windows

Откройте PowerShell в папке, где находятся `engine/`, `editor/` и `launch_editor.py`:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe launch_editor.py
```

Можно использовать `setup_windows.bat` и `start_editor.bat`. Если Python не нашёлся, проверьте `py --list` и `where python`.

## Установка macOS / Linux (запуск из исходников)

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python launch_editor.py
```

Qt и SDL2 могут потребовать установленных системных библиотек. Поддержка GUI зависит от платформы и графического стека.

## Первый проект

1. На Project Hub нажмите **Create Project**.
2. Укажите имя и каталог.
3. Выберите шаблон, например **2D Starter** или **3D Starter**.
4. После открытия найдите `scenes/main.vscene` и дерево нод слева.
5. Щёлкните ноду, чтобы увидеть её свойства в Inspector справа.
6. Используйте **Play In Editor** либо **Play Project (External)**.
7. Сохраните сцену `Ctrl+S` и проектные настройки через Project Settings.

## Что лежит в проекте

`project.vproject` хранит имя, настройки окна, runtime, ввод, сцены сборки и параметры экспорта. `scenes/` содержит сцены `.vscene`, `scripts/` — Python-скрипты, `assets/` — исходные ресурсы, `builds/` — экспортированные игры. В папке `.vworks/` находятся служебные данные и восстановление.

## Мини-проверка

Откройте `3D Starter`. В Scene Tree должны находиться камера, свет, окружение, пол, куб и сфера. Если изображение в Game View отличается от 3D viewport, проверьте настройки Game View в Project Settings: это две разные реализации предпросмотра.
