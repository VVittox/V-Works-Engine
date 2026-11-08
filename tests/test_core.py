from pathlib import Path
from engine.scene.node import Node, Node2D
from engine.scene.scene import Scene
from engine.scene.scene_tree import SceneTree
from engine.scene.signals import Signal
from engine.utils.vmath import Vector2

def test_node_paths_and_lookup():
    tree = SceneTree()
    scene = Scene('Main')
    player = Node('Player')
    weapon = Node('Weapon')
    player.add_child(weapon)
    scene.add_child(player)
    tree.set_current_scene(scene)
    assert weapon.path == '/Root/Main/Player/Weapon'
    assert scene.get_node('Player/Weapon') is weapon

def test_signal_bound_method_survives():
    signal = Signal('x')
    calls = []

    class Receiver:

        def cb(self, value):
            calls.append(value)
    receiver = Receiver()
    signal.connect(receiver.cb)
    assert signal.emit(7) == 1
    assert calls == [7]

def test_vector_cross():
    assert Vector2(1, 0).cross(Vector2(0, 1)) == 1

def test_scene_document_roundtrip(tmp_path):
    from editor.scene_document import SceneDocument
    from engine.scene import ColorRect2D, Scene
    from engine.utils.vmath import Vector2
    scene = Scene('EditorScene', (1, 2, 3))
    rect = ColorRect2D('Player', Vector2(120, 80), (10, 20, 30))
    rect.position = Vector2(44, -12)
    scene.add_child(rect)
    path = tmp_path / 'roundtrip.vscene'
    SceneDocument(scene).save(path)
    loaded = SceneDocument.load(path)
    child = loaded.scene.get_child(0)
    assert isinstance(child, ColorRect2D)
    assert child.name == 'Player'
    assert child.position == Vector2(44, -12)
    assert child.size == Vector2(120, 80)
    assert child.color == (10, 20, 30)

def test_project_config_create(tmp_path):
    from engine.core.project_config import ProjectConfig
    project = tmp_path / 'MyGame'
    cfg = ProjectConfig.create(project, 'My Game')
    assert (project / 'project.vproject').exists()
    assert cfg.main_scene_path.exists()
    loaded = ProjectConfig.load(project)
    assert loaded.name == 'My Game'
    assert loaded.window.width == 1280
    assert loaded.build.product_name == 'My Game'

def test_windows_build_plan_stages_project(tmp_path):
    from engine.core.project_config import ProjectConfig
    from editor.build_system import prepare_windows_build
    project = tmp_path / 'Game'
    cfg = ProjectConfig.create(project, 'Build Test')
    engine_root = Path(__file__).resolve().parents[1]
    plan = prepare_windows_build(cfg, engine_root, output_dir=tmp_path / 'out', onefile=True)
    assert plan.stage_dir.joinpath('project.vproject').exists()
    assert plan.stage_dir.joinpath('scenes', 'main.vscene').exists()
    assert 'PyInstaller' in plan.command
    assert '--onefile' in plan.command
    assert '--add-data' in plan.command

def test_build_scenes_order_and_migration(tmp_path):
    from engine.core.project_config import ProjectConfig
    from engine.scene import Scene
    from engine.scene.serialization import save_scene
    project = tmp_path / 'GameScenes'
    cfg = ProjectConfig.create(project, 'Scenes')
    second = project / 'scenes' / 'level2.vscene'
    save_scene(Scene('Level2'), second)
    cfg.add_build_scene(second)
    cfg.save()
    loaded = ProjectConfig.load(project)
    assert [s.path for s in loaded.enabled_build_scenes] == ['scenes/main.vscene', 'scenes/level2.vscene']
    assert loaded.scene_path(1) == second.resolve()

def test_extended_nodes_roundtrip(tmp_path):
    from engine.scene import Scene, Sprite2D, Label2D, Camera2DNode, CollisionRect2D
    from engine.physics import RigidBody2D
    from engine.scene.serialization import save_scene, load_scene
    scene = Scene('Extended')
    sprite = Sprite2D('Hero', 'assets/textures/hero.png')
    sprite.opacity = 0.5
    sprite.script_path = 'scripts/hero.py'
    label = Label2D('HUD', 'Score', 32)
    camera = Camera2DNode('Camera')
    camera.zoom = 2.0
    body = RigidBody2D('Box')
    body.mass = 3.0
    collision = CollisionRect2D('Hitbox')
    body.add_child(collision)
    for node in (sprite, label, camera, body):
        scene.add_child(node)
    path = tmp_path / 'extended.vscene'
    save_scene(scene, path)
    loaded = load_scene(path)
    hero = loaded.find_child('Hero')
    assert isinstance(hero, Sprite2D) and hero.texture_path.endswith('hero.png') and (hero.script_path == 'scripts/hero.py')
    assert isinstance(loaded.find_child('HUD'), Label2D)
    assert isinstance(loaded.find_child('Camera'), Camera2DNode)
    box = loaded.find_child('Box')
    assert isinstance(box, RigidBody2D) and box.mass == 3.0
    assert isinstance(box.find_child('Hitbox'), CollisionRect2D)

def test_script_attachment(tmp_path):
    from engine.scene import Scene, Node2D
    from engine.scripting import attach_project_scripts
    root = tmp_path
    scripts = root / 'scripts'
    scripts.mkdir()
    (scripts / 'move.py').write_text('from engine.scripting import VScript\nclass Script(VScript):\n    def _process(self, delta): self.owner.position.x += 10 * delta\n', encoding='utf-8')
    scene = Scene('Main')
    node = Node2D('Mover')
    node.script_path = 'scripts/move.py'
    scene.add_child(node)
    assert attach_project_scripts(scene, root, strict=True) == 1
    node._invoke_process(0.5)
    assert node.position.x == 5.0

def test_prefab_and_groups_roundtrip(tmp_path):
    from engine.scene import Node2D
    from engine.scene.serialization import save_prefab, load_prefab
    node = Node2D('Enemy')
    node.add_to_group('enemies')
    node.add_to_group('damageable')
    child = Node2D('Weapon')
    node.add_child(child)
    path = tmp_path / 'enemy.vprefab'
    save_prefab(node, path)
    loaded = load_prefab(path)
    assert loaded.name == 'Enemy'
    assert loaded.is_in_group('enemies')
    assert loaded.find_child('Weapon') is not None

def test_timer_runtime_node():
    from engine.scene import Timer
    timer = Timer()
    timer.wait_time = 0.1
    timer.one_shot = True
    calls = []
    timer.signals.connect('timeout', lambda: calls.append(1))
    timer.start()
    timer._process(0.2)
    assert calls == [1] and (not timer.running)

def test_tilemap_particles_navigation_and_ui_roundtrip(tmp_path):
    from engine.scene import Scene, TileMap2D, ParticleSystem2D, Navigation2D, UIPanel
    from engine.scene.serialization import save_scene, load_scene
    from engine.utils.vmath import Vector2
    scene = Scene('Advanced')
    tm = TileMap2D()
    tm.tile_size = Vector2(24, 24)
    tm.set_tile(2, 3, 7)
    tm.collision_tiles = {1, 7}
    scene.add_child(tm)
    particles = ParticleSystem2D()
    particles.amount = 8
    particles.emission_rate = 20
    scene.add_child(particles)
    nav = Navigation2D()
    nav.width = 8
    nav.height = 8
    nav.set_blocked(2, 2, True)
    scene.add_child(nav)
    panel = UIPanel()
    panel.set_anchor_preset('full_rect')
    panel.offset_left = 10
    panel.offset_top = 20
    panel.offset_right = -10
    panel.offset_bottom = -20
    scene.add_child(panel)
    path = tmp_path / 'advanced.vscene'
    save_scene(scene, path)
    loaded = load_scene(path)
    ltm = loaded.find_child('TileMap2D')
    assert isinstance(ltm, TileMap2D) and ltm.get_tile(2, 3) == 7 and (7 in ltm.collision_tiles)
    lp = loaded.find_child('ParticleSystem2D')
    lp._process(0.5)
    assert 0 < len(lp._particles) <= lp.amount
    ln = loaded.find_child('Navigation2D')
    route = ln.find_path(Vector2(16, 16), Vector2(7 * 32 + 16, 7 * 32 + 16))
    assert route and all((ln.world_to_cell(p) != (2, 2) for p in route))
    lpanel = loaded.find_child('UIPanel')
    pos, size = lpanel.resolved_rect(Vector2(800, 600))
    assert pos == Vector2(10, 20) and size == Vector2(780, 560)

def test_scene_inheritance_propagates_base_changes(tmp_path):
    from engine.scene import Scene, ColorRect2D
    from engine.scene.serialization import save_scene, load_scene, create_inherited_scene
    from engine.utils.vmath import Vector2
    base = Scene('Base')
    box = ColorRect2D('Box', Vector2(40, 40), (10, 20, 30))
    box.position = Vector2(5, 6)
    base.add_child(box)
    base_path = tmp_path / 'base.vscene'
    derived_path = tmp_path / 'derived.vscene'
    save_scene(base, base_path)
    create_inherited_scene(base_path, derived_path)
    derived = load_scene(derived_path)
    d = derived.find_child('Box')
    d.position = Vector2(99, 100)
    save_scene(derived, derived_path)
    base2 = load_scene(base_path)
    b = base2.find_child('Box')
    b.color = (200, 100, 50)
    b.size = Vector2(80, 70)
    save_scene(base2, base_path)
    reloaded = load_scene(derived_path)
    r = reloaded.find_child('Box')
    assert r.position == Vector2(99, 100)
    assert r.color == (200, 100, 50) and r.size == Vector2(80, 70)

def test_serialized_signal_connections(tmp_path):
    from engine.scene import Scene, Timer, Node
    from engine.scripting import attach_project_scripts, connect_scene_signals
    root = tmp_path
    scripts = root / 'scripts'
    scripts.mkdir()
    (scripts / 'receiver.py').write_text('from engine.scripting import VScript\nclass Script(VScript):\n    def __init__(self, owner): super().__init__(owner); owner.hit=0\n    def on_timeout(self): self.owner.hit += 1\n', encoding='utf-8')
    scene = Scene('Main')
    timer = Timer('Timer')
    receiver = Node('Receiver')
    receiver.script_path = 'scripts/receiver.py'
    scene.add_child(timer)
    scene.add_child(receiver)
    timer.signal_connections = [{'signal': 'timeout', 'target': '/Main/Receiver', 'method': 'on_timeout'}]
    attach_project_scripts(scene, root, strict=True)
    assert connect_scene_signals(scene, strict=True) == 1
    timer.wait_time = 0.01
    timer.one_shot = True
    timer.start()
    timer._process(0.1)
    assert receiver.hit == 1

def test_resource_material_roundtrip(tmp_path):
    from engine.resources import Material2D, VResource
    mat = Material2D.default()
    mat.data['shader_preset'] = 'pixelate'
    mat.data['params'] = {'pixel_size': 8}
    path = tmp_path / 'pixel.vmat'
    mat.save(path)
    loaded = VResource.load(path)
    assert loaded.resource_type == 'Material2D' and loaded.data['shader_preset'] == 'pixelate' and (loaded.data['params']['pixel_size'] == 8)

def test_project_templates_and_editor_settings(tmp_path):
    from engine.core.project_config import ProjectConfig
    from engine.scene.serialization import load_scene
    for template in ('platformer', 'top_down', 'ui_app', 'tilemap'):
        root = tmp_path / template
        cfg = ProjectConfig.create(root, template, template=template)
        cfg.editor.autosave_seconds = 30
        cfg.runtime.debug_collisions = True
        cfg.enabled_plugins = ['example']
        cfg.save()
        loaded = ProjectConfig.load(root)
        assert loaded.editor.autosave_seconds == 30 and loaded.runtime.debug_collisions and (loaded.enabled_plugins == ['example'])
        assert len(list(load_scene(loaded.main_scene_path).walk())) >= 2

def test_3d_scene_roundtrip(tmp_path):
    from engine.scene import Scene, Node3D, MeshInstance3D, Camera3DNode, DirectionalLight3D, WorldEnvironment3D
    from engine.scene.serialization import save_scene, load_scene
    from engine.utils.vmath import Vector3
    scene = Scene('ThreeD')
    root = Node3D('World')
    root.position = Vector3(1, 2, 3)
    mesh = MeshInstance3D('Cube', 'sphere')
    mesh.position = Vector3(4, 5, 6)
    mesh.rotation = Vector3(0.1, 0.2, 0.3)
    mesh.size = Vector3(2, 3, 4)
    mesh.color = (12, 34, 56)
    camera = Camera3DNode('Camera3D')
    camera.position = Vector3(0, 3, 8)
    camera.fov = 75
    light = DirectionalLight3D('Sun')
    env = WorldEnvironment3D('Environment')
    env.fog_enabled = True
    root.add_child(mesh)
    scene.add_child(root)
    scene.add_child(camera)
    scene.add_child(light)
    scene.add_child(env)
    path = tmp_path / '3d.vscene'
    save_scene(scene, path)
    loaded = load_scene(path)
    world = loaded.find_child('World')
    cube = loaded.find_child('Cube')
    assert isinstance(world, Node3D) and world.position == Vector3(1, 2, 3)
    assert isinstance(cube, MeshInstance3D) and cube.primitive == 'sphere'
    assert cube.position == Vector3(4, 5, 6) and cube.size == Vector3(2, 3, 4) and cube.color == (12, 34, 56)
    assert isinstance(loaded.find_child('Camera3D'), Camera3DNode)
    assert isinstance(loaded.find_child('Sun'), DirectionalLight3D)
    assert isinstance(loaded.find_child('Environment'), WorldEnvironment3D)


def test_3d_project_template(tmp_path):
    from engine.core.project_config import ProjectConfig
    from engine.scene import MeshInstance3D, Camera3DNode
    from engine.scene.serialization import load_scene
    cfg = ProjectConfig.create(tmp_path / 'Game3D', 'Game 3D', template='3d_starter')
    scene = load_scene(cfg.main_scene_path)
    assert any(isinstance(n, MeshInstance3D) for n in scene.walk())
    assert any(isinstance(n, Camera3DNode) for n in scene.walk())


def test_frozen_runtime_copy_export(tmp_path, monkeypatch):
    import sys
    from editor import build_system
    source = tmp_path / 'editor_dist'
    source.mkdir()
    exe = source / 'V Works Engine.exe'
    exe.write_bytes(b'MZ fake editor')
    internal = source / '_internal'
    internal.mkdir()
    (internal / 'runtime.dat').write_text('ok', encoding='utf-8')
    stage = tmp_path / 'stage'
    stage.mkdir()
    (stage / 'project.vproject').write_text('{"format":"vworks_project"}', encoding='utf-8')
    (stage / 'scenes').mkdir()
    (stage / 'scenes' / 'main.vscene').write_text('{}', encoding='utf-8')
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setattr(sys, 'executable', str(exe))
    monkeypatch.setattr(sys, '_MEIPASS', str(internal), raising=False)
    target = build_system.export_game_from_frozen_editor(stage, tmp_path / 'out', 'My Game')
    assert target.exists()
    assert target.name == 'My Game.exe'
    assert (target.parent / '_internal' / 'runtime.dat').exists()
    assert (target.parent / 'game_data' / 'project.vproject').exists()
    assert (target.parent / 'vworks_game_boot.json').exists()


def test_3d_physics_falls_onto_floor():
    from engine.core.settings import PhysicsSettings
    from engine.physics import PhysicsWorld, StaticBody3D, RigidBody3D
    from engine.scene import Scene
    from engine.utils.vmath import Vector3
    scene = Scene('Physics3D')
    floor = StaticBody3D('Floor')
    floor.position = Vector3(0, -0.5, 0)
    floor.collider.size = Vector3(10, 1, 10)
    box = RigidBody3D('Box')
    box.position = Vector3(0, 3, 0)
    box.collider.size = Vector3(1, 1, 1)
    scene.add_child(floor)
    scene.add_child(box)
    world = PhysicsWorld(PhysicsSettings())
    for _ in range(240):
        world.step(scene, 1 / 120)
    assert box.position.y >= 0.49
    assert box.position.y <= 0.55
    assert box.on_floor


def test_frozen_build_plan_uses_editor_export_backend(tmp_path, monkeypatch):
    import sys
    from editor.build_system import prepare_windows_build
    from engine.core.project_config import ProjectConfig
    project = tmp_path / 'Game'
    cfg = ProjectConfig.create(project, 'Game', template='empty')
    fake_exe = tmp_path / 'V Works Engine.exe'
    fake_exe.write_bytes(b'MZ fake')
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setattr(sys, 'executable', str(fake_exe))
    plan = prepare_windows_build(cfg, tmp_path, output_dir=tmp_path / 'out')
    assert plan.backend == 'frozen-runtime-copy'
    assert plan.command[0] == str(fake_exe)
    assert plan.command[1] == '--vworks-export-game'


def test_inverse_euler_roundtrip_multiple_axes():
    from engine.utils.vmath import Vector3, rotate_euler, inverse_rotate_euler
    v = Vector3(1.2, -3.4, 5.6)
    r = Vector3(0.37, -0.81, 0.44)
    restored = inverse_rotate_euler(rotate_euler(v, r), r)
    assert restored.distance_to(v) < 1e-8


def test_parented_camera_basis_sees_target():
    from engine.rendering.camera3d import Camera3D
    from engine.scene import Node3D, Camera3DNode
    from engine.utils.vmath import Vector3
    rig = Node3D('Rig')
    rig.position = Vector3(2, 1, 4)
    rig.rotation = Vector3(0.1, 0.55, 0.0)
    camera_node = Camera3DNode('Camera')
    camera_node.position = Vector3(0, 1, 5)
    rig.add_child(camera_node)
    target = camera_node.global_position + camera_node.global_forward * 10
    camera = Camera3D(position=camera_node.global_position, rotation=camera_node.global_rotation, source_node=camera_node)
    view = camera.world_to_view(target)
    assert abs(view.x) < 1e-8
    assert abs(view.y) < 1e-8
    assert view.z < -9.99


def test_3d_extras_roundtrip(tmp_path):
    from engine.scene import Scene, PointLight3D, SpotLight3D, RayCast3D, WorldEnvironment3D, Camera3DNode
    from engine.scene.serialization import save_scene, load_scene, SCENE_VERSION
    from engine.utils.vmath import Vector3
    scene = Scene('Extras')
    point = PointLight3D('Lamp')
    point.range = 12.5
    point.attenuation = 1.5
    spot = SpotLight3D('Spot')
    spot.spot_angle = 33
    ray = RayCast3D('Ray')
    ray.target_position = Vector3(1, 2, -9)
    env = WorldEnvironment3D('Env')
    env.sky_enabled = True
    env.sky_top_color = (1, 2, 3)
    camera = Camera3DNode('Camera')
    camera.cull_mask = 0x12345678
    for node in (point, spot, ray, env, camera):
        scene.add_child(node)
    path = tmp_path / 'extras.vscene'
    save_scene(scene, path)
    loaded = load_scene(path)
    assert SCENE_VERSION >= 5
    assert loaded.find_child('Lamp').range == 12.5
    assert loaded.find_child('Spot').spot_angle == 33
    assert loaded.find_child('Ray').target_position == Vector3(1, 2, -9)
    assert loaded.find_child('Env').sky_enabled
    assert loaded.find_child('Camera').cull_mask == 0x12345678


def test_raycast3d_hits_nearest_body():
    from engine.core.settings import PhysicsSettings
    from engine.physics import PhysicsWorld, StaticBody3D
    from engine.scene import Scene
    from engine.utils.vmath import Vector3
    scene = Scene('Ray')
    near = StaticBody3D('Near')
    near.position = Vector3(0, 0, -3)
    near.collider.size = Vector3(1, 1, 1)
    far = StaticBody3D('Far')
    far.position = Vector3(0, 0, -7)
    far.collider.size = Vector3(1, 1, 1)
    scene.add_child(near)
    scene.add_child(far)
    hit = PhysicsWorld(PhysicsSettings()).raycast_3d(scene, Vector3(), Vector3(0, 0, -10))
    assert hit is not None
    assert hit['body'] is near
    assert 2.4 < hit['distance'] < 2.6


def test_area3d_enter_exit_signals_once():
    from engine.core.settings import PhysicsSettings
    from engine.physics import PhysicsWorld, Area3D, RigidBody3D
    from engine.scene import Scene
    from engine.utils.vmath import Vector3
    scene = Scene('Area')
    area = Area3D('Trigger')
    area.collider.size = Vector3(4, 4, 4)
    body = RigidBody3D('Body')
    body.gravity_scale = 0
    body.position = Vector3(0, 0, 0)
    scene.add_child(area)
    scene.add_child(body)
    entered = []
    exited = []
    area.signals.connect('body_entered', lambda other: entered.append(other.name))
    area.signals.connect('body_exited', lambda other: exited.append(other.name))
    world = PhysicsWorld(PhysicsSettings())
    world.step(scene, 1 / 60)
    world.step(scene, 1 / 60)
    assert entered == ['Body']
    body.position = Vector3(20, 0, 0)
    world.step(scene, 1 / 60)
    assert exited == ['Body']


def test_ascii_stl_mesh_loader_and_asset_classification(tmp_path):
    from engine.rendering.mesh3d import Mesh3D
    from editor.asset_importer import AssetImporter
    stl = tmp_path / 'triangle.stl'
    stl.write_text('''solid triangle\nfacet normal 0 0 1\nouter loop\nvertex 0 0 0\nvertex 1 0 0\nvertex 0 1 0\nendloop\nendfacet\nendsolid triangle\n''', encoding='utf-8')
    mesh = Mesh3D.from_file(str(stl))
    assert len(mesh.vertices) == 3
    assert mesh.faces == [(0, 1, 2)]
    assert AssetImporter.classify(stl) == 'mesh3d'
