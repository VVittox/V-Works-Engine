# Python-скрипты и жизненный цикл

Игровой скрипт наследуется от `engine.scripting.VScript` и содержит класс с **точным именем `Script`**. Это условие загрузчика в `engine/scripting/script.py`. Скрипт указывается в `node.script_path` относительно корня проекта; редактор поддерживает Attach New Script и Script Editor.

## Пример

Файл `scripts/spin.py`:

```python
from engine.scripting import VScript

class Script(VScript):
    def _process(self, delta):
        self.owner.rotation.y += 0.7 * delta
```

Этот скрипт применим к `Node3D`, когда `rotation` является `Vector3`. Прикрепите его к вращающемуся 3D-объекту. В зависимости от внутреннего представления углов значение измеряется в радианах.

## Хуки

| Метод | Назначение |
|---|---|
| `_ready()` | Инициализация после входа ноды в сцену |
| `_process(delta)` | Обновление кадра; `delta` в секундах |
| `_physics_process(delta)` | Обновление физики с фиксированным шагом |
| `_draw(renderer)` | Дополнительная пользовательская отрисовка |
| `_exit_tree()` | Реакция на выход из дерева |

Также доступны `self.owner` (нода), `self.tree`, `self.engine`, `self.input`, `self.assets`, `self.properties` (параметры скрипта, хранящиеся в сцене).

## Ввод из скрипта

```python
from engine.scripting import VScript
from engine.utils.vmath import Vector2

class Script(VScript):
    def _process(self, delta):
        if self.input is None:
            return
        x = self.input.get_axis('ui_left', 'ui_right')
        y = self.input.get_axis('ui_up', 'ui_down')
        self.owner.position += Vector2(x, y) * (200 * delta)
```

Применяйте пример к `Node2D`. Для `CharacterBody2D` обычно правильнее назначать скорость и обрабатывать перемещение в physics tick, а не напрямую изменять transform.

## Сообщения и отладка

При ошибках импорта скрипта загрузчик может вывести `[VScript] Failed to attach …`. Включите Project Settings → Runtime → `strict_scripts` при необходимости получать исключение вместо мягкого продолжения. Проверяйте Output, Console и stdout при запуске из исходников. Скрипты выполняются как обычный Python-код с правами запущенного процесса — не устанавливайте сторонние непроверенные пакеты и скрипты.

## Структура импорта

```text
project/
  scripts/player.py
  scenes/main.vscene
  project.vproject
```

В `node.script_path` используйте `scripts/player.py`, не абсолютный путь к вашему компьютеру. Системы проекта автоматически получают корневую папку.
