# Каталог нод V Works Engine

Перечень отражает доступные классы исходников 0.11-preview. Для конкретных свойств смотрите Inspector и определения в `engine/scene/` и `engine/physics/`.

| Нода | Назначение | Типичные свойства / особенности |
|---|---|---|
| `Node` | Базовый логический объект | enabled, tag, groups, script_path |
| `Node2D` | Пространственная основа 2D | position, rotation, scale |
| `Node3D` | Пространственная основа 3D | position, rotation, scale, global_position |
| `Scene` | Корень сцены | Дерево дочерних нод |
| `Sprite2D` | Спрайт с текстурой | texture_path, centered, flip_h |
| `ColorRect2D` | Цветной прямоугольник | size, color |
| `Label2D` | Текст в 2D | text, font_size |
| `Camera2D` (`Camera2DNode`) | 2D-камера | Положение и масштаб |
| `CollisionRect2D` | Отладочная/сценическая форма | size, transform |
| `Timer` | Таймер и timeout | wait_time, one_shot, autostart |
| `Button2D` | Простая 2D-кнопка | text, size, pressed |
| `AudioStreamPlayer2D` | Воспроизведение аудио | stream_path, volume, loop |
| `TileMap2D` | Тайловая карта | tiles, tile_size, atlas_columns |
| `ParticleSystem2D` | Частицы | amount, emission_rate, lifetime, direction |
| `Light2D` | 2D-освещение | position и настройки света |
| `CanvasModulate` | Модуляция 2D-канвы | Цвет окружающей сцены |
| `CanvasLayer` | Слой UI | Дочерние элементы Control |
| `Control` | База для адаптивного UI | anchors, offsets |
| `UIPanel` | Контейнер | anchors, offsets |
| `UILabel` | Текст Control | text, font_size |
| `UICanvas` | Canvas с размером эталона | reference_size |
| `UIImage` | UI-изображение | texture_path, fill_amount |
| `UIButton` | UI-кнопка | text, disabled, pressed |
| `VideoPlayer` | Проигрывание клипа | clip_path, autoplay, loop |
| `Navigation2D` | Навигационная область | Регионы/пути |
| `NavigationAgent2D` | Агент пути | Цель/маршрут |
| `StaticBody2D` | Статическая 2D-физика | collider, collision_layer |
| `RigidBody2D` | Динамическая 2D-физика | velocity, mass, friction |
| `CharacterBody2D` | Управляемое 2D-тело | velocity, on_ground |
| `Area2D` | Зона-триггер 2D | collider.is_trigger |
| `MeshInstance3D` | Примитив или 3D-меш | primitive, mesh_path, size, color |
| `Camera3D` (`Camera3DNode`) | 3D-камера | current, fov, near, far, orthographic |
| `DirectionalLight3D` | Направленный свет | color, energy, ambient |
| `PointLight3D` | Точечный свет | color, range, attenuation |
| `SpotLight3D` | Прожектор | spot_angle, edge_softness |
| `WorldEnvironment3D` | Мир, небо и туман | sky_enabled, fog_enabled, ambient_energy |
| `Marker3D` | Точка/маркер в 3D | position |
| `RayCast3D` | Луч/проверка препятствия | target_position, collision_mask, colliding |
| `Path3D` | Ломаный путь в 3D | points |
| `PathFollow3D` | Движение по Path3D | progress, speed, loop |
| `LookAt3D` | Поворот к цели | target_path |
| `StaticBody3D` | Статическая 3D-физика | collider.size |
| `RigidBody3D` | Динамическая 3D-физика | velocity, mass |
| `CharacterBody3D` | Управляемое 3D-тело | velocity, collider |
| `Area3D` | 3D-триггер | collider.is_trigger |

## Создание нод

В редакторе Scene → Add Node. При программном создании экземпляры создаются обычным Python-кодом и присоединяются через `parent.add_child(node)`.

## Замечание о функциях

Наличие класса ноды **не гарантирует** одинаковый уровень реализации в 2D и 3D: например, некоторые 3D-эффекты и редакторские gizmo находятся в разработке. В документации ноды описаны по реальным классам, а не как обещание полного аналога Unreal/Godot.
