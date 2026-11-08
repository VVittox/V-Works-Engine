from pathlib import Path
from unittest.mock import patch
import gc,math,random,tempfile,unittest,weakref
from engine.scene import Scene,Node,Node3D,MeshInstance3D,Camera3DNode,PointLight3D
from engine.scene.scene_tree import SceneTree
from engine.physics import PhysicsWorld,StaticBody3D,RigidBody3D,Area3D,StaticBody2D,RigidBody2D
from engine.physics.body import BodyType
from engine.physics.broadphase import SpatialBroadphase
from engine.core.settings import PhysicsSettings
from engine.utils.vmath import Vector2,Vector3
from engine.rendering.cache3d import GeometryCache3D,TransformCache3D,point
from engine.rendering.projection3d import Projection3D
from engine.rendering.camera3d import Camera3D
from engine.rendering.renderer import PygameRenderer

class BroadphaseTests(unittest.TestCase):
    def test_random_grid_never_misses_a_possible_collision(self):
        rng=random.Random(901)
        for dim in (2,3):
            bodies=[]
            for i in range(180):
                cls=(StaticBody3D if i%3 else RigidBody3D) if dim==3 else (StaticBody2D if i%3 else RigidBody2D)
                body=cls();vector=Vector3 if dim==3 else Vector2
                body.position=vector(*(rng.uniform(-40,40) for _ in range(dim)))
                body.collider.size=vector(*(rng.uniform(.2,15) for _ in range(dim)))
                body.collider.is_trigger=i%13==0;bodies.append(body)
            pairs=SpatialBroadphase(bodies,dim,4).pairs();self.assertEqual(pairs,sorted(set(pairs)))
            actual=set(pairs)
            for i,a in enumerate(bodies):
                for j,b in enumerate(bodies[i+1:],i+1):
                    if a.body_type is BodyType.STATIC and b.body_type is BodyType.STATIC and not (a.collider.is_trigger or b.collider.is_trigger):continue
                    if a.collider.overlaps(a.global_position,b.collider,b.global_position):self.assertIn((i,j),actual)

    def test_huge_floor_does_not_expand_into_millions_of_cells(self):
        floor=StaticBody3D();floor.collider.size=Vector3(100000,1,100000)
        body=RigidBody3D();body.position=Vector3(0,.5,0)
        grid=SpatialBroadphase([floor,body],3,4)
        self.assertLess(len(grid.cells),10);self.assertEqual(grid.pairs(),[(0,1)])

    def test_sparse_thousand_bodies_has_no_quadratic_pair_list(self):
        scene=Scene()
        for i in range(1000):
            body=RigidBody3D() if i%10==0 else StaticBody3D()
            body.position=Vector3((i%50)*10,0,(i//50)*10);body.gravity_scale=0;scene.add_child(body)
        world=PhysicsWorld(PhysicsSettings());world.step(scene,1/60)
        self.assertLess(world.stats['candidate_pairs_3d'],1000)
        scene.get_child(0).position=scene.get_child(1).position
        world.step(scene,1/60);self.assertGreater(world.stats['candidate_pairs_3d'],0)

    def test_trigger_enters_once_even_when_solver_runs_many_iterations(self):
        scene=Scene();area=Area3D();area.collider.size=Vector3(20,20,20);scene.add_child(area)
        for _ in range(3):
            body=RigidBody3D();body.gravity_scale=0;scene.add_child(body)
        entered=[];area.signals.connect('body_entered',lambda b:entered.append(b))
        world=PhysicsWorld(PhysicsSettings(iterations=8));world.step(scene,0)
        self.assertEqual(len(entered),3);self.assertEqual(len(set(entered)),3)

    def test_solver_matches_bruteforce_for_separated_falling_boxes(self):
        def make():
            root=Scene();floor=StaticBody3D();floor.position.y=-.5;floor.collider.size=Vector3(200,1,200);root.add_child(floor)
            for i in range(12):
                b=RigidBody3D();b.position=Vector3(i*3,1+i*.1,0);root.add_child(b)
            return root
        a,b=make(),make();one=PhysicsWorld(PhysicsSettings());two=PhysicsWorld(PhysicsSettings())
        class Brute:
            def __init__(self,bodies,*_):self.bodies=bodies
            def pairs(self):return [(i,j) for i in range(len(self.bodies)) for j in range(i+1,len(self.bodies))]
        for _ in range(60):
            one.step(a,1/60)
            with patch('engine.physics.world.SpatialBroadphase',Brute):two.step(b,1/60)
        for x,y in zip(a.get_children(),b.get_children()):
            self.assertLess((x.position-y.position).length,1e-9)

    def test_2d_floor_and_trigger_masks_remain_correct(self):
        from engine.physics import Area2D
        root=Scene();floor=StaticBody2D();floor.position=Vector2(0,100);floor.collider.size=Vector2(500,20)
        box=RigidBody2D('Box');box.position=Vector2(20,20);box.collider.size=Vector2(10,10)
        area=Area2D();area.collider.size=Vector2(50,99)
        for n in (floor,box,area):n.collision_layer=2;n.collision_mask=2;root.add_child(n)
        entered=[];exited=[];area.signals.connect('body_entered',lambda n:entered.append(n));area.signals.connect('body_exited',lambda n:exited.append(n))
        world=PhysicsWorld(PhysicsSettings())
        for _ in range(180):world.step(root,1/120)
        self.assertAlmostEqual(box.position.y,90);self.assertTrue(box.on_ground);self.assertEqual(entered,[box])
        box.collision_mask=0;world.step(root,0);self.assertEqual(exited,[box])

class CacheTests(unittest.TestCase):
    def test_nested_transform_matches_public_api_and_mutable_vectors(self):
        cache=TransformCache3D();rng=random.Random(13);parent=Node3D();bridge=Node();parent.add_child(bridge);node=Node3D();bridge.add_child(node)
        for _ in range(30):
            for n in (parent,node):
                n.position=Vector3(*(rng.uniform(-10,10) for _ in range(3)));n.rotation=Vector3(*(rng.uniform(-3,3) for _ in range(3)))
                n.scale=Vector3(2,-.7,1.3)
            v=Vector3(1,2,3);self.assertLess((point(cache.matrix(node),v)-node.to_global(v)).length,1e-9)
            parent.position.x+=3;self.assertLess((point(cache.matrix(node),v)-node.to_global(v)).length,1e-9)
        other=Node3D();other.position.y=45;other.add_child(node)
        self.assertLess((point(cache.matrix(node),v)-node.to_global(v)).length,1e-9)

    def test_geometry_cache_invalidates_parent_size_and_rotation(self):
        cache=GeometryCache3D();parent=Node3D();n=MeshInstance3D();parent.add_child(n);mesh=cache.mesh(n,Path.cwd())
        old=cache.entry(n,mesh).prepare();self.assertIs(cache.entry(n,mesh),old)
        for obj,attr in ((parent.position,'x'),(n.rotation,'z'),(n.size,'y')):
            setattr(obj,attr,getattr(obj,attr)+.3);new=cache.entry(n,mesh).prepare();self.assertIsNot(old,new);old=new
            for a,b in zip(new.vertices,mesh.vertices):
                self.assertLess((a-n.to_global(Vector3(b.x*n.size.x,b.y*n.size.y,b.z*n.size.z))).length,1e-9)

    def test_file_asset_reloads_after_one_frame_and_primitives_are_shared(self):
        cache=GeometryCache3D();a=MeshInstance3D();b=MeshInstance3D()
        self.assertIs(cache.mesh(a,Path.cwd()),cache.mesh(b,Path.cwd()))
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as tmp:
            p=Path(tmp)/'a.obj';p.write_text('v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n');a.mesh_path='a.obj'
            first=cache.mesh(a,tmp);p.write_text('v 0 0 0\nv 22 0 0\nv 0 1 0\nf 1 2 3\n');cache.begin_frame()
            second=cache.mesh(a,tmp);self.assertIsNot(first,second);self.assertEqual(second.vertices[1].x,22)

    def test_removed_nodes_are_not_kept_alive_by_geometry_caches(self):
        cache=GeometryCache3D();root=Scene();n=MeshInstance3D();root.add_child(n);mesh=cache.mesh(n,Path.cwd())
        cache.entry(n,mesh).prepare();ref=weakref.ref(n);root.remove_child(n);del n;gc.collect()
        self.assertIsNone(ref());self.assertEqual(len(cache.nodes),0);self.assertEqual(len(cache.transforms.entries),0)

class ProjectionTests(unittest.TestCase):
    def test_sphere_culling_keeps_large_partial_objects(self):
        view=Projection3D.from_camera(Camera3D(position=Vector3()),1280,720)
        self.assertTrue(view.sphere_visible(Vector3(20,0,-10),20))
        self.assertFalse(view.sphere_visible(Vector3(100,0,-10),1))
        self.assertFalse(view.sphere_visible(Vector3(0,0,10),1))

    def test_polygon_clips_all_six_planes_in_both_projections(self):
        for orthographic in (False,True):
            view=Projection3D.from_camera(Camera3D(position=Vector3(),orthographic=orthographic,far=30),1280,720)
            vertices=[Vector3(-100,-100,-.001),Vector3(100,-100,-2),Vector3(100,100,-50),Vector3(-100,100,-2)]
            clipped=view.clip(vertices);self.assertGreaterEqual(len(clipped),3)
            for vertex in clipped:
                p=view.project_view(vertex);self.assertIsNotNone(p)
                self.assertGreaterEqual(p[0],-1e-6);self.assertLessEqual(p[0],1280+1e-6)
                self.assertGreaterEqual(p[1],-1e-6);self.assertLessEqual(p[1],720+1e-6)

    def test_hidden_parent_hides_lights_and_runtime_respects_cull_mask(self):
        class Screen:
            def get_size(self):return 1280,720
        r=PygameRenderer.__new__(PygameRenderer);r.screen=Screen();r.project_root=Path.cwd();r.camera3d=Camera3D()
        r._triangles3d=[];r._point_lights3d=[];r._spot_lights3d=[]
        root=Scene();parent=Node3D();parent.visible=False;parent.add_child(PointLight3D());root.add_child(parent)
        r.prepare_scene_3d(root);self.assertEqual(r._point_lights3d,[])
        mesh=MeshInstance3D();mesh.position=Vector3(1000,0,-10);root.add_child(mesh)
        r.queue_mesh_3d(mesh);self.assertEqual(r.render_stats['culled'],1);self.assertEqual(r._triangles3d,[])
        mesh.position=Vector3(0,2,0);r.queue_mesh_3d(mesh);self.assertTrue(r._triangles3d)
        r._triangles3d.clear();r.camera3d.cull_mask=0;r.queue_mesh_3d(mesh);self.assertFalse(r._triangles3d)

    def test_warm_geometry_updates_with_camera_parent_and_light_changes(self):
        class Screen:
            def get_size(self):return 1280,720
        r=PygameRenderer.__new__(PygameRenderer);r.screen=Screen();r.project_root=Path.cwd();r.camera3d=Camera3D()
        r._triangles3d=[];r._point_lights3d=[];r._spot_lights3d=[]
        root=Scene();parent=Node3D();mesh=MeshInstance3D();parent.add_child(mesh);root.add_child(parent);mesh.position.y=2
        r.prepare_scene_3d(root);r.queue_mesh_3d(mesh);before=[p[1] for p in r._triangles3d]
        r._triangles3d.clear();r.camera3d.position.x+=1;r.queue_mesh_3d(mesh)
        self.assertNotEqual(before,[p[1] for p in r._triangles3d])
        r._triangles3d.clear();parent.position.x+=1;r.queue_mesh_3d(mesh)
        self.assertEqual(before,[p[1] for p in r._triangles3d])
        r._triangles3d.clear();mesh.color=(255,0,0);r.queue_mesh_3d(mesh)
        self.assertTrue(all(p[2][0]>0 and p[2][2]==0 for p in r._triangles3d))
        r._triangles3d.clear();mesh.color=(0,0,255);r.queue_mesh_3d(mesh)
        self.assertTrue(all(p[2][2]>0 and p[2][0]==0 for p in r._triangles3d))
        cached=[p[2] for p in r._triangles3d];r._triangles3d.clear()
        r.set_directional_light_3d(Vector3(1,0,0),ambient=.8);r.queue_mesh_3d(mesh)
        self.assertNotEqual(cached,[p[2] for p in r._triangles3d])

    def test_projection_tracks_parented_camera_after_rotation_and_scale(self):
        parent=Node3D();parent.rotation=Vector3(.3,.7,-.4);parent.scale=Vector3(1.4,.7,-1.2)
        camera=Camera3DNode();camera.position=Vector3(2,3,4);parent.add_child(camera)
        from types import SimpleNamespace
        renderer=SimpleNamespace(camera3d=Camera3D());camera.sync_renderer(renderer)
        for angle in (.7,1.1):
            parent.rotation.y=angle;camera.sync_renderer(renderer)
            view=Projection3D.from_camera(renderer.camera3d,1280,720)
            target=camera.global_position+camera.global_forward*10
            p=view.project(target);self.assertAlmostEqual(p[0],640);self.assertAlmostEqual(p[1],360)

    def test_side_clipping_keeps_large_floor_depth_and_fog_order(self):
        class Screen:
            def get_size(self):return 1280,720
        r=PygameRenderer.__new__(PygameRenderer);r.screen=Screen();r.project_root=Path.cwd();r.camera3d=Camera3D()
        r._triangles3d=[];r._point_lights3d=[];r._spot_lights3d=[];r.prepare_scene_3d(Scene())
        r.camera3d.position=Vector3(0,5,6);r.camera3d.rotation=Vector3(-.35,0,0);r.camera3d.orthographic=True
        floor=MeshInstance3D('floor','plane');floor.size=Vector3(100,1,100);floor.position=Vector3(0,-.2,-10);floor.shaded=False
        mesh=r._geometry_cache_3d().mesh(floor,Path.cwd())
        vertices=[r.camera3d.world_to_view(floor.to_global(Vector3(v.x*100,v.y,v.z*100))) for v in mesh.vertices]
        depth_vertices=r._clip_camera_polygon(vertices);expected=-sum(v.z for v in depth_vertices)/len(depth_vertices)
        r.queue_mesh_3d(floor);self.assertEqual(len(r._triangles3d),1);self.assertAlmostEqual(r._triangles3d[0][0],expected)

if __name__=='__main__':unittest.main()
