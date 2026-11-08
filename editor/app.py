from __future__ import annotations
import sys
from pathlib import Path
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication
from .editor_settings import Appearance
from .main_window import MainWindow
from .project_manager import ProjectManagerWindow

def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName('V Works Engine')
    app.setOrganizationName('VVittox')
    Appearance.load().apply(app)
    resources = Path(__file__).resolve().parent / 'resources'
    icon = resources / 'vworks_icon.png'
    if icon.exists():
        app.setWindowIcon(QIcon(str(icon)))
    if len(sys.argv) > 1:
        project = Path(sys.argv[1]).resolve()
        if project.is_file():
            project = project.parent
        window = MainWindow(project, resources_dir=resources)
    else:
        window = ProjectManagerWindow(resources)
    window.show()
    return app.exec()
if __name__ == '__main__':
    raise SystemExit(main())
