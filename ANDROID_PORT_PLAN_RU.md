# V Works Engine → Android: план порта

**Текущее состояние:** экспорт APK/AAB не реализован. Имеется только подготовка исходного пакета через `tools/prepare_android_bundle.py`.

## Почему нельзя сразу собрать APK

- Движок запускает сцену в desktop Pygame/SDL2, а отдельный редактор работает на desktop PySide6/Qt.
- Экспериментальный GPU backend использует desktop OpenGL 3.3 и offscreen ModernGL context, не OpenGL ES на Android.
- Для Android необходимы собственная упаковка зависимостей, жизненный цикл Android activity, сенсорный ввод, хранение файлов и адаптация звука.

## Реалистичный порядок работ

1. Разделить чистые игровой runtime/сцены и GUI-редактор, отдельно проверить импорты `engine` без Qt.
2. Выбрать подтверждённый Android Python runtime + SDL2 (либо Qt for Python Android с отдельным Qt render path); проверить зависимости на **физическом Android устройстве**.
3. Добавить GLES-compatible 3D renderer (OpenGL ES 3.x, глубина, простые материалы), выбор графического бэкенда по платформе.
4. Реализовать Android game loop/surface lifecycle и паузу/возврат при смене приложения.
5. Перенести input: touch, мультитач, экранные элементы управления и геймпады.
6. Настроить формирование и подпись APK/AAB, проверки архитектур ARM64, размер и performance.

Qt официально предоставляет `pyside6-android-deploy`, но это **не** кнопка «собрать любое Pygame-приложение» — приложение должно использовать поддерживаемый Qt Android стек. Смотрите актуальные требования на https://doc.qt.io/qtforpython-6/deployment/deployment-pyside6-android-deploy.html

## Уже подготовлено

Android stage включает `engine/`, `game_data/`, манифест с текущими ограничениями, чтобы использовать его при портировании. Его не следует переименовывать в `.apk`: Android не сможет установить этот ZIP как приложение.
