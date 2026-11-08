# Сборка редактора и экспорт игр

Это **два разных процесса**. Редактор как приложение можно упаковать через PyInstaller; игры экспортируются из меню Build согласно настройкам `project.vproject`.

## Windows: редактор в один EXE

1. Распакуйте ZIP целиком.
2. Убедитесь, что рядом находятся `engine/`, `editor/`, `launch_editor.py`, `requirements.txt` и `V Works Engine Onefile.spec`.
3. На Windows дважды запустите **`build_editor_onefile.bat`**.
4. BAT создаст `.venv` при необходимости, установит зависимости и запустит PyInstaller.
5. Ищите **`dist/V Works Engine.exe`**.

Spec использует `onefile`-структуру `EXE(...)`, `console=False` и `editor/resources/vworks_icon.ico`. Один EXE может долго распаковывать библиотечные файлы во временный каталог при запуске. Onefile ≠ отсутствие временной распаковки.

Если exe не запускается, соберите **`build_editor_onedir_debug.bat`**, чтобы увидеть stdout/stderr. Windows Defender или ограничения доступа тоже могут блокировать новую неподписанную программу.

## Windows: экспорт игры

Откройте проект → Project Settings → Build Scenes → убедитесь, что нужные сцены включены и путь `main_scene` верен → Build → Build Windows. У игры свои настройки `onefile`, `debug_console`, версия, название и иконка; их не следует путать с `V Works Engine Onefile.spec` редактора.

Уже упакованный редактор может использовать отдельную схему frozen-runtime export для игры. Если однокомпонентный exe редактора не умеет собирать самодостаточный onefile-экспорт игры, используйте исходный Python runtime и проверяйте результат на чистой Windows-машине.

## macOS

Запуск из исходников: установите Python и зависимости на Mac. Экспорт через `python tools/export_macos.py <проект>` выполняется на macOS. `.app` нельзя достоверно построить/протестировать в Linux-контейнере или Windows без соответствующей macOS-среды.

## Android

`python tools/prepare_android_bundle.py <проект>` создаёт исходный ZIP для будущего мобильного runtime. Это **не APK**. Для APK нужны отдельные Android entry point, совместимый SDL/рендер, поддержка касаний, упакованные зависимости и тесты на реальном устройстве. См. `ANDROID_PORT_PLAN_RU.md`.

## Проблемы сборки

| Симптом | Что проверить |
|---|---|
| `No module named PyInstaller` | Установлена ли зависимость в активной `.venv` |
| Иконка не видна | Есть ли `editor/resources/vworks_icon.ico`; иногда Windows кэширует значки |
| Экран не появляется | Используйте onedir debug и проверьте логи |
| Не хватает `.vscene` при экспорте | Build Scenes и пути внутри каталога проекта |
| Нет GPU | Установите `requirements-gpu.txt`, проверьте OpenGL-драйвер; CPU остаётся доступным |
| `py` не найден | Установите Python и используйте `python -m venv .venv` |
