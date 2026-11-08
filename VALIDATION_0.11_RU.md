# Проверка V Works Engine 0.11-preview

## Основа архива

- Последний пользовательский `V Works Engine(2).zip`: файлы редактора, проекта, тестов и скриптов.
- Недостающее ядро `engine/` восстановлено из предыдущего `V_Works_Engine_0_10_Preview.zip`.
- Более свежие файлы последнего пользовательского ZIP имели приоритет.

## Что реально проверено в текущей среде

- Python `compileall`: все Python-файлы синтаксически корректны.
- `pytest` для `test_core.py`, `test_new_features.py`, `test_templates_v011.py`, `test_performance.py`, `test_appearance_v011.py`: **71 passed, 1 skipped**.
- Сохранение, загрузка и повторная загрузка всех 19 шаблонов.
- Режим Python-комментариев: после токенизации **0 `COMMENT` tokens** в `.py`; удалены также 28 исходных docstrings (информацию перенесли в отдельные документы).
- Исправлена обработка GPU-атрибута при headless-тестировании, где `PygameRenderer` создаётся без вызова `__init__`.
- Windows spec проверен статически: `console=False`, иконка и структура onefile без `COLLECT`.

## Что не проверялось

- GUI-smoke-test и реальные темы в PySide6: пакет PySide6 отсутствует в проверочной среде; соответствующие Qt-тесты пропущены.
- Запуск SDL2/Pygame, видеокарта и GPU-FPS: зависимостей и графического окружения здесь нет.
- Создание Windows EXE: сборка BAT/PyInstaller предназначена для Windows и не выполнялась в Linux.
- Создание/проверка готового macOS `.app` и Android APK: не выполнялось, мобильного runtime пока нет.

## Как повторить тесты на компьютере

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest -q tests\nbuild_editor_onefile.bat
```

Для pytest при необходимости поставьте `pytest` в `.venv`. Для экспериментов с GPU установите `requirements-gpu.txt` и включите OpenGL-бэкенд в Project Settings. Перед тестами сохраните резервную копию своего проекта.
