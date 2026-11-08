# V Works Engine 0.11 Preview

V Works Engine — редактор и экспериментальный игровой движок на Python. Редактор использует **PySide6 / Qt**, игровой runtime — **Pygame / SDL2**. Доступны 2D-сцены и экспериментальный 3D-пайплайн с CPU- и OpenGL-бэкендами.

**Начните с [документации](docs/INDEX_RU.md)**. В ней описаны установка, интерфейс, ноды, система сцен, 2D/3D, сценарии, импорт ресурсов, шаблоны и сборка.

## Быстрый запуск

На Windows откройте `start_editor.bat` или выполните:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe launch_editor.py
```

Для экспериментального OpenGL-бэкенда:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-gpu.txt
```

В Project Manager создайте проект из одного из **19 учебных шаблонов**. Четыре готовых учебных проекта также находятся в `example_projects/` и открываются через Open / Import Folder. Персональные темы и масштаб шрифта находятся в **Editor Settings**. Сохранение и компоновка dock-панелей доступны между сеансами.

## Сборка редактора в один EXE

На Windows запустите **`build_editor_onefile.bat`**. Готовый файл ожидается в `dist/V Works Engine.exe`. Это **скрипт сборки, а не готовый EXE**: Windows и установленные зависимости необходимы для выполнения сборки. Для отладки есть `build_editor_onedir_debug.bat`.

## Совместимость и оговорки

- GPU-растеризация экспериментальная: преобразование мешей и часть освещения выполняются на CPU, затем изображение считывается обратно в Pygame.
- Сборка `.app` для macOS выполняется на macOS; Android source bundle **не является APK**.
- Для сохранности своих проектов перед обновлением движка делайте копию. Исходники из последнего пользовательского архива дополнены ядром из предыдущей сборки, потому что в последнем ZIP папка `engine/` отсутствовала.

## Версия

0.11-preview — расширение редактора, темы, шаблоны, документация и Windows onefile packaging. Подробности в [CHANGELOG](docs/CHANGELOG_RU.md).

Подробный отчёт о выполненных проверках — [VALIDATION_0.11_RU.md](VALIDATION_0.11_RU.md).
