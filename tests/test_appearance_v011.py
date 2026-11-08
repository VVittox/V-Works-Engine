from __future__ import annotations

import pytest

pytest.importorskip('PySide6')

from editor.editor_settings import ACCENTS, THEMES, Appearance


def test_appearance_generates_qss_for_all_themes():
    for theme in THEMES:
        for accent in ACCENTS:
            css = Appearance(theme, accent).stylesheet()
            assert 'QDockWidget' in css
            assert 'QTreeWidget' in css
            assert 'QStatusBar' in css
            assert '#ffffff' in css


def test_appearance_density_changes_padding():
    compact = Appearance(density='Compact').stylesheet()
    spacious = Appearance(density='Spacious').stylesheet()
    assert compact != spacious
