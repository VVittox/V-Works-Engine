from __future__ import annotations
from pathlib import Path
from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QFileDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget, QComboBox, QListWidgetItem, QMainWindow, QMessageBox, QPushButton, QVBoxLayout, QWidget, QDialog, QDialogButtonBox
from engine.core.project_config import ProjectConfig, PROJECT_FILE
from .main_window import MainWindow
from .editor_settings import EditorSettingsDialog
from engine.core.project_templates import TEMPLATES, get_template
class CreateProjectDialog(QDialog):

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle('Create V Works Project')
        self.resize(620, 210)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.name = QLineEdit('My Game')
        self.template = QComboBox()
        for item in TEMPLATES:
            self.template.addItem(f'{item.category}  /  {item.title}', item.id)
            self.template.setItemData(self.template.count() - 1, item.description, Qt.ToolTipRole)
        self.location = QLineEdit(str(Path.home() / 'Documents' / 'VWorksProjects' / 'MyGame'))
        row = QHBoxLayout()
        row.addWidget(self.location, 1)
        browse = QPushButton('Browse…')
        browse.clicked.connect(self._browse)
        row.addWidget(browse)
        form.addRow('Project name', self.name)
        form.addRow('Template', self.template)
        form.addRow('Project folder', row)
        layout.addLayout(form)
        self.template_info = QLabel('')
        self.template_info.setObjectName('muted')
        self.template_info.setWordWrap(True)
        layout.addWidget(self.template_info)
        self.template.currentIndexChanged.connect(self._update_template_info)
        self._update_template_info()
        hint = QLabel('V Works will create project.vproject, scenes/, assets/, scripts/ and builds/.')
        hint.setWordWrap(True)
        layout.addWidget(hint)
        buttons = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.name.textChanged.connect(self._name_changed)
        self._manual_location = False
        self.location.textEdited.connect(lambda _: setattr(self, '_manual_location', True))

    def _update_template_info(self) -> None:
        spec = get_template(str(self.template.currentData()))
        self.template_info.setText(f'{spec.description}\nLearn: {", ".join(spec.features)}')

    def _name_changed(self, value: str) -> None:
        if self._manual_location:
            return
        safe = ''.join((ch for ch in value if ch.isalnum() or ch in ' _-')).strip().replace(' ', '_') or 'MyGame'
        self.location.setText(str(Path.home() / 'Documents' / 'VWorksProjects' / safe))

    def _browse(self) -> None:
        path = QFileDialog.getExistingDirectory(self, 'Choose Project Folder', str(Path(self.location.text()).parent))
        if path:
            self._manual_location = True
            self.location.setText(path)

class ProjectManagerWindow(QMainWindow):

    def __init__(self, resources_dir: str | Path) -> None:
        super().__init__()
        self.resources_dir = Path(resources_dir)
        self.settings = QSettings('VVittox', 'V Works Engine')
        self._editor = None
        self.setWindowTitle('V Works Engine — Project Manager')
        self.resize(930, 610)
        icon = self.resources_dir / 'vworks_icon.png'
        if icon.exists():
            self.setWindowIcon(QIcon(str(icon)))
        root = QWidget()
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(28, 24, 28, 24)
        outer.setSpacing(14)
        logo_path = self.resources_dir / 'vworks_logo_wide.png'
        if logo_path.exists():
            logo = QLabel()
            pm = QPixmap(str(logo_path))
            logo.setPixmap(pm.scaledToWidth(430, Qt.TransformationMode.SmoothTransformation))
            logo.setAlignment(Qt.AlignCenter)
            outer.addWidget(logo)
        title = QLabel('V Works Engine')
        title.setStyleSheet('font-size: 30px; font-weight: 800; color: #75b9ff;')
        subtitle = QLabel('')
        subtitle.setObjectName('muted')
        outer.addWidget(title)
        outer.addWidget(subtitle)
        self.project_search = QLineEdit()
        self.project_search.setPlaceholderText('Search recent projects…')
        self.project_search.textChanged.connect(self._filter_projects)
        outer.addWidget(self.project_search)
        self.projects = QListWidget()
        self.projects.setAlternatingRowColors(True)
        self.projects.itemDoubleClicked.connect(lambda _: self.open_selected())
        outer.addWidget(self.projects, 1)
        buttons = QHBoxLayout()
        create = QPushButton('+ Create Project')
        create.setObjectName('primary')
        create.clicked.connect(self.create_project)
        import_btn = QPushButton('Open / Import Folder')
        import_btn.clicked.connect(self.import_project)
        remove = QPushButton('Remove from List')
        remove.clicked.connect(self.remove_selected)
        edit = QPushButton('Edit Project')
        edit.setObjectName('primary')
        edit.clicked.connect(self.open_selected)
        buttons.addWidget(create)
        buttons.addWidget(import_btn)
        buttons.addWidget(remove)
        settings_btn = QPushButton('Editor Settings')
        settings_btn.clicked.connect(lambda: EditorSettingsDialog(self).exec())
        buttons.addWidget(settings_btn)
        buttons.addStretch(1)
        buttons.addWidget(edit)
        outer.addLayout(buttons)
        self._reload()

    def _filter_projects(self, search: str) -> None:
        needle = search.casefold().strip()
        for index in range(self.projects.count()):
            item = self.projects.item(index)
            item.setHidden(needle not in item.text().casefold())

    def _recent(self) -> list[str]:
        value = self.settings.value('recent_projects', [])
        if isinstance(value, str):
            value = [value]
        return [str(Path(p).resolve()) for p in value if p]

    def _save_recent(self, paths: list[str]) -> None:
        unique = []
        for p in paths:
            if p not in unique:
                unique.append(p)
        self.settings.setValue('recent_projects', unique[:30])

    def _add_recent(self, path: str | Path) -> None:
        p = str(Path(path).resolve())
        self._save_recent([p] + [x for x in self._recent() if x != p])
        self._reload(select=p)

    def _reload(self, select: str | None=None) -> None:
        self.projects.clear()
        existing = []
        for p in self._recent():
            root = Path(p)
            if not (root / PROJECT_FILE).exists():
                continue
            existing.append(str(root))
            try:
                cfg = ProjectConfig.load(root)
                label = f'{cfg.name}\n{root}'
            except Exception:
                label = f'{root.name}\n{root}'
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, str(root))
            self.projects.addItem(item)
            if select and str(root) == select:
                self.projects.setCurrentItem(item)
        self._save_recent(existing)
        self._filter_projects(self.project_search.text())
        if self.projects.count() and self.projects.currentItem() is None:
            self.projects.setCurrentRow(0)

    def create_project(self) -> None:
        dialog = CreateProjectDialog(self)
        if dialog.exec() != QDialog.Accepted:
            return
        root = Path(dialog.location.text()).expanduser().resolve()
        name = dialog.name.text().strip() or root.name
        try:
            if root.exists() and any(root.iterdir()) and (not (root / PROJECT_FILE).exists()):
                answer = QMessageBox.question(self, 'Folder is not empty', 'Create a V Works project inside this non-empty folder?', QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if answer != QMessageBox.Yes:
                    return
            ProjectConfig.create(root, name, self.resources_dir, template=str(dialog.template.currentData()))
            self._add_recent(root)
            self._open(root)
        except Exception as exc:
            QMessageBox.critical(self, 'Create project failed', str(exc))

    def import_project(self) -> None:
        path = QFileDialog.getExistingDirectory(self, 'Open V Works Project Folder', str(Path.home()))
        if not path:
            return
        root = Path(path).resolve()
        try:
            if not (root / PROJECT_FILE).exists():
                answer = QMessageBox.question(self, 'Initialize Project?', 'No project.vproject was found. Initialize this folder as a V Works project?', QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
                if answer != QMessageBox.Yes:
                    return
                ProjectConfig.load_or_create(root, self.resources_dir)
            else:
                ProjectConfig.load(root)
            self._add_recent(root)
            self._open(root)
        except Exception as exc:
            QMessageBox.critical(self, 'Open project failed', str(exc))

    def selected_path(self) -> Path | None:
        item = self.projects.currentItem()
        return Path(item.data(Qt.UserRole)) if item else None

    def open_selected(self) -> None:
        path = self.selected_path()
        if path is not None:
            self._open(path)

    def remove_selected(self) -> None:
        path = self.selected_path()
        if path is None:
            return
        self._save_recent([p for p in self._recent() if Path(p).resolve() != path.resolve()])
        self._reload()

    def _open(self, root: Path) -> None:
        try:
            self._editor = MainWindow(root, resources_dir=self.resources_dir)
            self._editor.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
            self._editor.destroyed.connect(self._editor_closed)
            self._editor.show()
            self.hide()
            self._add_recent(root)
        except Exception as exc:
            QMessageBox.critical(self, 'Editor failed', str(exc))

    def _editor_closed(self, *args) -> None:
        self._editor = None
        self._reload()
        self.show()
        self.raise_()
        self.activateWindow()
