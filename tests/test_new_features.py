from array import array
import json
from pathlib import Path
import zipfile
import pytest

from engine.scene import Path3D, PathFollow3D, LookAt3D, Scene
from engine.scene.serialization import node_from_dict, node_to_dict
from engine.core.project_config import ProjectConfig
from engine.rendering.gpu3d import GpuTriangles3D
from engine.utils.vmath import Vector3
from tools.export_macos import prepare_macos_command
from tools.prepare_android_bundle import prepare_bundle


def test_path3d_sampling_and_loop():
    node = Path3D()
    node.points = [Vector3(0,0,0),Vector3(10,0,0)]
    assert abs(node.length-10.0)<1e-9
    assert abs(node.sample(3.5).x-3.5)<1e-9
    assert abs(node.sample(100).x-10.0)<1e-9
    assert abs(node.sample(12,wrap=True).x-2.0)<1e-9


def test_pathfollow_scene_update():
    scene = Scene()
    path = scene.add_child(Path3D('Route'))
    path.points = [Vector3(0,0,0),Vector3(0,0,-10)]
    follower = path.add_child(PathFollow3D('Mover'))
    follower.speed = 2
    follower._process(1.5)
    assert follower.progress == 3
    assert abs(follower.global_position.z + 3) < 1e-9


def test_new_nodes_serialize_without_loss():
    scene = Scene()
    path = scene.add_child(Path3D('Route'))
    path.points = [Vector3(1,2,3),Vector3(9,8,7)]
    path.closed = True
    follower = path.add_child(PathFollow3D('Mover'))
    follower.speed = 12
    follower.path_node = '..'
    follower.progress = 5
    tracker = scene.add_child(LookAt3D('Tracker'))
    tracker.target_path = '../Route'
    copy = node_from_dict(node_to_dict(scene))
    p = copy.find_child('Route')
    f = copy.find_child('Mover')
    t = copy.find_child('Tracker')
    assert isinstance(p,Path3D) and p.closed and p.points[1].z==7
    assert isinstance(f,PathFollow3D) and f.speed==12 and f.progress==5
    assert isinstance(t,LookAt3D) and t.target_path=='../Route'


def sample_project(tmp_path):
    project = tmp_path/'game';project.mkdir()
    cfg = ProjectConfig.create(project, 'V Works Test Game')
    cfg.runtime.render_backend = 'gpu'
    cfg.save()
    return project


def test_render_backend_persists(tmp_path):
    project = sample_project(tmp_path)
    cfg = ProjectConfig.load(project)
    assert cfg.runtime.render_backend == 'gpu'
    payload=json.loads((project/'project.vproject').read_text())
    assert payload['runtime']['render_backend']=='gpu'


def test_macos_build_command_stages_project(tmp_path):
    project=sample_project(tmp_path)
    cmd, app=prepare_macos_command(project,host_check=False)
    assert '--windowed' in cmd
    assert app.suffix=='.app'
    assert (project/'.vworks/build/macos/game_data/project.vproject').exists()
    assert (project/'.vworks/build/macos/game_data/build_manifest.json').exists()


def test_android_stages_sources_not_apk(tmp_path):
    project=sample_project(tmp_path)
    bundle=prepare_bundle(project)
    assert bundle.suffix=='.zip'
    with zipfile.ZipFile(bundle) as z:
        assert 'engine/runtime_game.py' in z.namelist()
        assert 'game_data/project.vproject' in z.namelist()
        report=json.loads(z.read('ANDROID_STATUS.json'))
        assert report['status']=='source_staging_only_not_apk'


def test_gpu_triangulates_a_quad_without_opengl():
    g=GpuTriangles3D.__new__(GpuTriangles3D)
    g.vertices = array('f')
    g.add_face([Vector3(0,0,-1),Vector3(1,0,-1),
                Vector3(1,1,-1),Vector3(0,1,-1)],(255,128,0))
    assert len(g.vertices)==2*3*6
    assert g.vertices[3]==1.0
