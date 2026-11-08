# Учебные проекты (Templates)

Project Hub → **Create Project** → **Template**. Каждый пункт создаёт обычный проект с `project.vproject`, `scenes/main.vscene`, ресурсными папками и `TEMPLATE_GUIDE.md`. Встроенные стартовые скрипты используются только там, где они предусмотрены конкретным шаблоном.

| Группа | Шаблоны | Тема урока |
|---|---|---|
| Basics | Empty 2D, 2D Starter | Сцена и базовые ноды |
| 2D Games | 2D Platformer, Top Down 2D, TileMap World | Движение, ввод, карта |
| 2D Labs | Physics Sandbox, Particle Playground, 2D Lighting Studio, Signals & Timers, Navigation Lab | Физика, свет, эффекты, маршруты, сигналы |
| UI | UI Application, UI Dashboard | Canvas, Control, anchors, адаптивность |
| 3D | 3D Starter | Камера, свет, примитивы |
| 3D Games | 3D Arena Starter, Third Person 3D, 3D Obstacle Course | Пространство, блок-аут, объект игрока |
| 3D Labs | 3D Physics Lab, 3D Lighting Studio, RayCast 3D Lab | Физика, свет, ray queries |

Всего **19 шаблонов**. В описании каждого в диалоге создания перечислены изучаемые узлы.

## Практика: физика 3D

Создайте **3D Physics Lab** и запустите. Посмотрите `Floor` с `StaticBody3D` и дочерние `DynamicBody` с `RigidBody3D`. Меняйте `gravity_3d` в Project Settings и проверяйте поведение. Можно изучать свойства Collider в Inspector.

## Практика: 3D Arena

Создайте **3D Arena Starter**. Он содержит пол, ограждения, укрытия, свет, камеру и несколько `Marker3D` для точек появления. Это **блок-аут**, а не готовый шутер: управление героем, волны и боевая логика пишутся отдельно.

## Практика: UI

Создайте **UI Dashboard**, изучите `CanvasLayer`, `UIPanel`, `UILabel`. Измените размеры окна, чтобы понять смысл `anchor_left`, `anchor_right`, смещений и вложенности элементов.

## Как сделать из шаблона свою игру

Создайте проект → сохраните сцену → добавьте игровые сущности → прикрепите скрипты → настройте Input Map → укажите Build Scenes → экспортируйте. Шаблоны — только стартовая база и учебный материал; они не притворяются готовыми играми и не копируют чужие проекты.

## Готовые примеры внутри архива

В папке `example_projects/` уже находятся четыре проекта: `Arena_3D`, `Physics_2D`, `Dashboard_UI`, `Lighting_3D`. Их можно открыть через Project Hub → Open / Import Folder, не создавая заново.
