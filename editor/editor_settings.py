from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import QApplication, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLabel, QSpinBox, QVBoxLayout


THEMES = {
    'Midnight': ('#171c26', '#202735', '#293344', '#354258', '#e8eef8', '#9aaac1', '#4b9dff'),
    'Graphite': ('#1d1e22', '#292b31', '#34373e', '#444953', '#eceff3', '#aeb6c2', '#78a8fa'),
    'Ocean': ('#102330', '#173344', '#204256', '#31566a', '#e9f6fb', '#a9c3d1', '#42c8d6'),
    'Light': ('#e8edf3', '#f7f9fc', '#ffffff', '#b9c6d5', '#253143', '#607186', '#2768ba'),
}

ACCENTS = {
    'Blue': '#4b9dff',
    'Cyan': '#33c6cf',
    'Violet': '#a78bfa',
    'Emerald': '#42bf87',
    'Orange': '#f4a35c',
}


@dataclass(frozen=True)
class Appearance:
    theme: str = 'Midnight'
    accent: str = 'Blue'
    font_size: int = 10
    density: str = 'Comfortable'

    @classmethod
    def load(cls) -> 'Appearance':
        settings = QSettings('VVittox', 'V Works Engine')
        theme = str(settings.value('appearance/theme', 'Midnight'))
        accent = str(settings.value('appearance/accent', 'Blue'))
        density = str(settings.value('appearance/density', 'Comfortable'))
        try:
            font_size = int(settings.value('appearance/font_size', 10))
        except (ValueError, TypeError):
            font_size = 10
        return cls(theme if theme in THEMES else 'Midnight', accent if accent in ACCENTS else 'Blue', max(8, min(18, font_size)), density if density in ('Compact', 'Comfortable', 'Spacious') else 'Comfortable')

    def save(self) -> None:
        settings = QSettings('VVittox', 'V Works Engine')
        settings.setValue('appearance/theme', self.theme)
        settings.setValue('appearance/accent', self.accent)
        settings.setValue('appearance/font_size', self.font_size)
        settings.setValue('appearance/density', self.density)
        settings.sync()

    def stylesheet(self) -> str:
        background, panel, control, border, foreground, muted, default_accent = THEMES[self.theme]
        accent = ACCENTS[self.accent] if self.theme != 'Ocean' else default_accent
        selected = QColor(accent).darker(175).name()
        padding = {'Compact': 3, 'Comfortable': 6, 'Spacious': 9}[self.density]
        tab_pad = padding + 4
        return f'''
QMainWindow, QDialog, QWidget {{ background-color: {background}; color: {foreground}; }}
QMenuBar, QMenu, QToolBar, QStatusBar {{ background-color: {panel}; color: {foreground}; border: 0; }}
QMenuBar::item:selected, QMenu::item:selected {{ background-color: {selected}; }}
QToolBar {{ spacing: 5px; padding: 5px; border-bottom: 1px solid {border}; }}
QDockWidget {{ color: {foreground}; font-weight: 500; }}
QDockWidget::title {{ background-color: {panel}; padding: 7px; border-bottom: 1px solid {border}; }}
QTabWidget::pane {{ border: 1px solid {border}; }}
QTabBar::tab {{ background-color: {panel}; color: {muted}; padding: {tab_pad}px 17px; border: 1px solid {border}; border-bottom: 0; }}
QTabBar::tab:selected {{ background-color: {control}; color: {accent}; border-top: 2px solid {accent}; }}
QTabBar::tab:hover {{ color: {foreground}; }}
QTreeWidget, QTreeView, QListWidget, QTableWidget, QPlainTextEdit, QTextEdit, QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
    background-color: {control}; color: {foreground}; border: 1px solid {border}; border-radius: 5px;
    selection-background-color: {selected}; selection-color: #ffffff;
}}
QTreeWidget, QTreeView, QListWidget {{ alternate-background-color: {panel}; outline: none; }}
QTreeWidget::item, QTreeView::item {{ padding: {max(2, padding - 2)}px; }}
QTreeWidget::item:selected, QTreeView::item:selected, QListWidget::item:selected {{ background-color: {selected}; }}
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{ padding: {padding}px; }}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{ border: 1px solid {accent}; }}
QPushButton, QToolButton {{ background-color: {control}; color: {foreground}; border: 1px solid {border}; border-radius: 6px; padding: {padding}px {padding + 5}px; }}
QPushButton:hover, QToolButton:hover {{ border-color: {accent}; }}
QPushButton:pressed, QToolButton:checked, QPushButton#primary {{ background-color: {selected}; border-color: {accent}; color: #ffffff; }}
QPushButton:disabled, QToolButton:disabled {{ color: {muted}; }}
QLabel#muted {{ color: {muted}; }}
QGroupBox {{ border: 1px solid {border}; border-radius: 7px; margin-top: 12px; padding-top: 10px; }}
QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 4px; color: {accent}; }}
QSplitter::handle {{ background-color: {border}; }}
QScrollBar:vertical {{ background: {panel}; width: 10px; }}
QScrollBar:horizontal {{ background: {panel}; height: 10px; }}
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{ background: {border}; border-radius: 4px; min-height: 24px; min-width: 24px; }}
QStatusBar {{ border-top: 1px solid {border}; color: {muted}; }}
QToolTip {{ background-color: {control}; color: {foreground}; border: 1px solid {accent}; padding: 5px; }}
'''

    def apply(self, app: QApplication | None = None) -> None:
        app = app or QApplication.instance()
        if app is None:
            return
        font = QFont(app.font())
        font.setPointSize(self.font_size)
        app.setFont(font)
        app.setStyleSheet(self.stylesheet())


class EditorSettingsDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle('Editor Settings — Appearance')
        self.setMinimumWidth(420)
        current = Appearance.load()
        layout = QVBoxLayout(self)
        heading = QLabel('Editor appearance')
        heading.setStyleSheet('font-size: 17px; font-weight: 700;')
        layout.addWidget(heading)
        hint = QLabel('Preferences are saved for all projects and restored on launch.')
        hint.setWordWrap(True)
        hint.setObjectName('muted')
        layout.addWidget(hint)
        form = QFormLayout()
        self.theme = QComboBox()
        self.theme.addItems(THEMES)
        self.theme.setCurrentText(current.theme)
        self.accent = QComboBox()
        self.accent.addItems(ACCENTS)
        self.accent.setCurrentText(current.accent)
        self.font_size = QSpinBox()
        self.font_size.setRange(8, 18)
        self.font_size.setSuffix(' pt')
        self.font_size.setValue(current.font_size)
        self.density = QComboBox()
        self.density.addItems(('Compact', 'Comfortable', 'Spacious'))
        self.density.setCurrentText(current.density)
        form.addRow('Theme', self.theme)
        form.addRow('Accent color', self.accent)
        form.addRow('Font size', self.font_size)
        form.addRow('Interface density', self.density)
        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _save(self) -> None:
        appearance = Appearance(self.theme.currentText(), self.accent.currentText(), self.font_size.value(), self.density.currentText())
        appearance.save()
        appearance.apply()
        self.accept()
