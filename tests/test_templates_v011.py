from __future__ import annotations

from pathlib import Path

import pytest

from engine.core.project_config import ProjectConfig
from engine.core.project_templates import TEMPLATES, get_template
from engine.scene.serialization import load_scene


@pytest.mark.parametrize('template', TEMPLATES, ids=lambda item: item.id)
def test_template_project_create_and_roundtrip(tmp_path, template):
    project = tmp_path / template.id
    cfg = ProjectConfig.create(project, template.title, template=template.id)
    assert cfg.path.exists()
    assert cfg.main_scene_path.exists()
    assert (project / 'TEMPLATE_GUIDE.md').exists()
    assert 'Learn:' not in (project / 'TEMPLATE_GUIDE.md').read_text(encoding='utf-8')
    scene = load_scene(cfg.main_scene_path)
    assert scene.name == 'Main'
    assert len(tuple(scene.walk())) >= (1 if template.id == 'empty' else 3)
    loaded = ProjectConfig.load(project)
    assert loaded.name == template.title
    assert loaded.main_scene_path == cfg.main_scene_path


def test_template_ids_are_unique():
    ids = [template.id for template in TEMPLATES]
    assert len(ids) == 19
    assert len(set(ids)) == len(ids)
    assert all(template.features and template.description for template in TEMPLATES)
    assert get_template('arena_3d').title == '3D Arena Starter'


def test_onefile_spec_sets_windowed_icon():
    root = Path(__file__).resolve().parents[1]
    text = (root / 'V Works Engine Onefile.spec').read_text(encoding='utf-8')
    assert 'console=False' in text
    assert "icon='editor/resources/vworks_icon.ico'" in text
    assert 'COLLECT(' not in text
    assert (root / 'editor/resources/vworks_icon.ico').exists()
    bat = (root / 'build_editor_onefile.bat').read_text(encoding='utf-8')
    assert 'V Works Engine Onefile.spec' in bat
    assert 'dist\\V Works Engine.exe' in bat
