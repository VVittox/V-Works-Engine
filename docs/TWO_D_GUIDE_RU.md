# 2D в V Works Engine

## Прямоугольники, текст и спрайты

`ColorRect2D` полезен для прототипирования: задайте `position`, `size`, `color`. `Sprite2D` выводит изображение по `texture_path`, путь обычно задаётся относительно папки проекта. `Label2D` используется для коротких подписей и HUD в простых прототипах.

## Физика

`StaticBody2D` — неподвижные объекты, `RigidBody2D` — объекты с динамикой, `CharacterBody2D` — управляемый объект. У каждого физического тела есть `collider`, `velocity`, `collision_layer`, `collision_mask`; динамическим телам доступны масса, трение, импульсы. `Area2D` позволяет сделать триггер. В `Physics Sandbox` есть три падающих блока и статический пол.

Пример изменения ускорения:

```python
from engine.utils.vmath import Vector2

body.velocity = Vector2(120, -240)
body.apply_impulse(Vector2(0, -30))
```

Перед этим `body` должен быть ссылкой на 2D-физическую ноду, для которой применимы эти методы.

## TileMap2D

`TileMap2D` хранит словарь тайлов, размер ячейки и параметры атласа. Укажите `texture_path`, `atlas_columns`, `tile_size`. Методы `set_tile(x, y, id)`, `erase_tile(x, y)`, `get_tile(x, y)` изменяют сетку. Используйте панель TileMap в редакторе. `debug_grid=True` помогает видеть границы.

## ParticleSystem2D

Настройте `amount`, `emission_rate`, `lifetime`, `speed_min`, `speed_max`, `direction`, `spread`, `gravity`, `color_start`, `color_end`. В `Particle Playground` находятся два эмиттера. Метод `restart()` сбрасывает частицы.

## Навигация

Ноды `Navigation2D` и `NavigationAgent2D` служат основой для поиска пути в 2D. Используйте `Navigation Lab`, чтобы исследовать доступные свойства и визуальные препятствия. Одно только добавление этих нод не создаёт сложный AI: логику агента и настройку проходимости требуется реализовать в проекте.

## 2D-UI

Для простой статической разметки подходят `CanvasLayer`, `Control`, `UIPanel`, `UILabel`. Anchor отвечает за относительное положение внутри родителя, Offset — за пиксельные смещения. Более новые `UICanvas`, `UIImage`, `UIButton` дают дополнительные варианты масштабирования и UI-изображений. В движке существуют и `Button2D` для простой экранной кнопки.

## Ввод

Действия `ui_left`, `ui_right`, `ui_up`, `ui_down`, `ui_accept`, `ui_cancel` настроены по умолчанию. Дополнительные действия назначайте через Project → Input Map. Не привязывайте игровой код к физическим клавишам без необходимости: действия проще перенастроить.
