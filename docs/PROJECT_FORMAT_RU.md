# Формат проекта и структура файлов

V Works хранит проекты в файловых каталогах. Основной конфигурационный файл — `project.vproject`, JSON с `format: "vworks_project"` и версией формата. В `engine/core/project_config.py` определены классы `ProjectConfig`, `ProjectWindowConfig`, `ProjectRuntimeConfig`, `ProjectBuildConfig`, `ProjectEditorConfig`.

## Пример минимального файла

```json
{
  "format": "vworks_project",
  "version": 3,
  "name": "MyGame",
  "main_scene": "scenes/main.vscene",
  "icon": "icon.png",
  "runtime": {"target_fps": 120, "physics_fps": 60, "render_backend": "cpu"},
  "build": {"product_name": "MyGame", "scenes": [{"path": "scenes/main.vscene", "enabled": true}]}
}
```

Отсутствующие значения `ProjectConfig.load` заполняет значениями по умолчанию. Рекомендуется менять настройки через интерфейс — там реализованы валидация и сохранение.

## Основные секции

- `window`: width, height, fullscreen, borderless, resizable, vsync.
- `runtime`: target_fps, physics_fps, gravity, gravity_3d, preview_backend, render_backend, debug-параметры и background_color.
- `build`: product_name, version, company, onefile, debug_console, clean_build, exclude, scenes.
- `input_map`: действие → список клавиш.
- `editor`: autosave_enabled, autosave_seconds, recovery_keep, grid_size, show_collision_shapes.
- `tags`, `layers`, `enabled_plugins`: классификация нод и расширения.

## Сцены

Сцены `.vscene` сериализуются средствами `engine/scene/serialization.py`. Ноды имеют имя, тип и свойства, затем дерево дочерних нод. Для повторного использования существуют префабы и наследование сцен. Редактировать вручную можно, но ошибки в JSON и несовместимые свойства могут нарушить загрузку.

## Папки

```text
MyGame/
  project.vproject
  icon.png
  TEMPLATE_GUIDE.md
  scenes/main.vscene
  scripts/
  assets/textures/
  assets/audio/
  assets/materials/
  assets/shaders/
  assets/prefabs/
  assets/tilesets/
  addons/
  builds/
  .vworks/imports/
  .vworks/autosave/
```

Папка `builds/` предназначена для результатов экспорта. Не включайте в исходный репозиторий большие временные сборки и локальную `.venv/`, если они не нужны.
