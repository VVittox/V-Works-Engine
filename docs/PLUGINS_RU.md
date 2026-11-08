# Плагины и расширения

Подключаемые плагины хранятся в `addons/<plugin_name>/`. Каждый плагин содержит `plugin.json` с метаданными и Python-модуль. В редакторе откройте Project → Package / Plugin Manager, чтобы просмотреть, установить ZIP и включить расширение.

## Пример manifest

```json
{
  "id": "example.tools",
  "name": "Example Tools",
  "version": "1.0.0",
  "entry": "plugin.py",
  "description": "Small editor extension"
}
```

## Пример кода

Файл `addons/example_tools/plugin.py`:

```python
def register(editor):
    editor.log('Example Tools loaded')

def unregister(editor):
    editor.log('Example Tools unloaded')
```

Плагин включается в `enabled_plugins` проекта. `PluginHost` сканирует `addons/*/plugin.json`, импортирует выбранные модули и вызывает `register(editor)`. При завершении редактора вызывается `unregister(editor)`, если он определён.

## Безопасность

Плагины выполняют полноценный Python-код в процессе редактора. Устанавливайте только расширения из доверенных источников, проверяйте файлы, не открывайте случайные ZIP как плагины. Для экспериментов лучше создать отдельный тестовый проект.

## Границы API

Прямое обращение к внутренностям `MainWindow` может нарушиться при обновлении движка. В 0.11-preview нет стабильного публичного ABI плагинов; документированные точки входа `register` и `unregister` не равны полной гарантии совместимости API.
