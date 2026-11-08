# Сцены, дерево объектов и сигналы

**Scene** — корневая нода игры или части уровня. Каждая нода может содержать дочерние объекты. Базовый класс `Node` поддерживает `add_child`, `remove_child`, `get_children`, `walk`, `path`, группы, теги, слой, включение/выключение и события жизненного цикла.

## Наследование нод

- `Node`: логика без пространственных координат.
- `Node2D`: позиция/поворот/масштаб в 2D.
- `Node3D`: позиция/поворот/масштаб в 3D, локальные и глобальные преобразования.
- Специализированные ноды расширяют эти базовые классы: физика, визуальные элементы, камера, свет и другие.

## Работа с деревом в коде

```python
from engine.scene import Scene, Node2D
from engine.utils.vmath import Vector2

scene = Scene('Level')
player = Node2D('Player')
player.position = Vector2(150, 200)
player.tag = 'Player'
player.add_to_group('Actors')
scene.add_child(player)

for node in scene.walk():
    print(node.path)
```

## Inspector

Выберите ноду в Scene Tree: справа откроются ее параметры. При перемещении объекта через gizmo или числовые поля изменения применяются к текущей сцене. После изменения используйте `Ctrl+S`. К некоторым нодам доступны специализированные окна (TileMap, Navigation, сигналы).

## Сигналы

Сигнал описывает событие: у `Timer` есть `timeout`, у `Button2D` — `pressed`, у 2D/3D-физики — сигналы контактов. Реализация находится в `engine/scene/signals.py`, соединения редактора — в Scene → Signals. Программный пример:

```python
from engine.scene import Timer

timer = Timer('Countdown')
timer.wait_time = 1.0
timer.signals.connect('timeout', lambda: print('Tick'))
timer.start()
```

## Группы и слои

`tag` — текстовая классификация. `groups` — набор групп, в которые можно добавить ноду. `layer` и `collision_layer`/`collision_mask` используются разными подсистемами; не путайте слой отрисовки и маску физических столкновений.

## Префабы и наследование

В Scene Tree выберите объект → **Save Selected as Prefab**. В другой сцене используйте **Instantiate Prefab**. Наследуемую сцену можно создать через **Create Inherited Scene**. По окончании проверьте относительные пути к ресурсам и скриптам: они разрешаются относительно корня проекта.
