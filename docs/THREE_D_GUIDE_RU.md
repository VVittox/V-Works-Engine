# 3D в V Works Engine

3D-подсистема поддерживает примитивы и загрузку некоторых 3D-мешей, камеры, базовый свет, окружение, простую 3D-физику и raycast. Это экспериментальная система, не функциональный аналог современных коммерческих движков.

## Объекты

`Node3D` хранит позицию, вращение и масштаб. `MeshInstance3D` задаёт `primitive`, `mesh_path`, `size`, `color`, `wireframe`, `shaded`, `double_sided`, `segments`, `rings`. Поддерживаемые примитивы можно посмотреть в Inspector и в `engine/rendering/mesh3d.py`. Для 3D-прототипов быстрее всего начать с cube и sphere.

## Камера

`Camera3DNode` позволяет выбрать `current`, `fov`, `near`, `far`, перспективную или ортографическую проекцию и маску отображения `cull_mask`. В сцене выбирайте активную камеру; в редакторском 3D viewport есть режим Camera Preview (`P`). Изменяйте FOV постепенно: слишком широкий угол может сильно искажать картинку.

## Освещение и атмосфера

`DirectionalLight3D` моделирует направленный свет. `PointLight3D` имеет диапазон действия и затухание. `SpotLight3D` расширяет точечный свет углом прожектора. `WorldEnvironment3D` управляет ambient, небом и туманом; такие настройки как `fog_near`, `fog_far` позволяют создать глубину сцены. В `3D Lighting Studio` можно сравнить типы света.

## Коллизии и физика

`StaticBody3D` — неподвижный коллайдер, `RigidBody3D` — динамическое тело, `CharacterBody3D` — управляемый объект, `Area3D` — зона триггера. Задавайте коллайдер соразмерно визуальному мешу; коллизия не возникает автоматически только из-за наличия `MeshInstance3D`. В `3D Physics Lab` уже настроены пол и тела.

## RayCast3D

`RayCast3D` использует `target_position`, `collision_mask`, `exclude_parent`, `enabled`. После `force_raycast_update()` можно проверять `colliding`, `collider`, `collision_point` и `collision_normal`. В `RayCast 3D Lab` размещён луч и несколько целей. Перед эксплуатацией убедитесь, что цели имеют коллайдеры.

## Path3D / PathFollow3D / LookAt3D

`Path3D` хранит последовательность 3D-точек. `PathFollow3D` перемещает дочерние объекты вдоль пути, `LookAt3D` ориентирует объект на другую ноду. Инспектор предоставляет соответствующие свойства; точные имена и значения см. в `engine/scene/path3d.py`.

## Первый 3D-уровень

Создайте `3D Starter`; оставьте `WorldEnvironment3D`, `DirectionalLight3D` и `Camera3D`. Добавьте несколько `StaticBody3D` с `MeshInstance3D` как дочерними визуальными элементами. Добавьте `Marker3D` для появления игрока. В Project Settings проверьте `gravity_3d` и 3D renderer. Запустите игру и затем возвращайтесь в редактор для правок.
