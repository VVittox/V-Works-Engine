import math,unittest
from engine.scene import Node,Node3D
from engine.rendering.projection3d import Projection3D
from engine.rendering.camera3d import Camera3D
from engine.utils.vmath import Vector3
from editor.transform_gizmo import TransformDrag,plane_hit,triangle_hit

class ManipulationTests(unittest.TestCase):
    def view(self,orthographic=False):
        return Projection3D.from_camera(Camera3D(position=Vector3(0,0,10),orthographic=orthographic),1280,720)

    def test_screen_plane_follows_camera_in_perspective_and_orthographic(self):
        for ortho in (False,True):
            n=Node3D();view=self.view(ortho);drag=TransformDrag(n,view,(640,360));drag.update((720,310))
            projected=view.project(n.global_position)
            self.assertAlmostEqual(projected[0],720);self.assertAlmostEqual(projected[1],310);self.assertEqual(n.position.z,0)

    def test_axis_lock_keeps_other_world_coordinates(self):
        n=Node3D();n.position=Vector3(.17,.21,-.5);view=self.view();p=view.project(n.position)
        drag=TransformDrag(n,view,p[:2],constraint='X');drag.update((p[0]+100,p[1]-60))
        self.assertEqual(n.position.y,.21);self.assertEqual(n.position.z,-.5);self.assertGreater(n.position.x,.17)

    def test_depth_axis_can_be_moved_when_facing_it_head_on(self):
        n=Node3D();drag=TransformDrag(n,self.view(),(640,360),constraint='Z');drag.update((640,290))
        self.assertEqual(n.position.x,0);self.assertEqual(n.position.y,0);self.assertGreater(n.position.z,0)

    def test_grid_uses_total_drag_instead_of_rounding_each_tiny_event(self):
        n=Node3D();view=self.view();drag=TransformDrag(n,view,(640,360),constraint='X')
        for x in range(641,741):drag.update((x,360),snap=.5)
        many=n.position.x;n.position=Vector3();other=TransformDrag(n,view,(640,360),constraint='X');other.update((740,360),snap=.5)
        self.assertEqual(n.position.x,many);self.assertGreater(many,.5)

    def test_world_move_under_rotated_scaled_parent_and_generic_bridge(self):
        parent=Node3D();parent.rotation=Vector3(.2,.7,-.5);parent.scale=Vector3(2,.7,-1.4)
        bridge=Node();parent.add_child(bridge);n=Node3D();bridge.add_child(n)
        view=self.view();drag=TransformDrag(n,view,(640,360),constraint='X');drag.update((740,320))
        world=n.global_position;self.assertAlmostEqual(world.y,0);self.assertAlmostEqual(world.z,0);self.assertGreater(world.x,0)

    def test_local_axis_and_plane_respect_parent_orientation(self):
        parent=Node3D();parent.rotation.z=math.pi/2;n=Node3D();parent.add_child(n)
        drag=TransformDrag(n,self.view(),(640,360),constraint='X',local=True);drag.update((640,270))
        self.assertGreater(n.global_position.y,0);self.assertAlmostEqual(n.global_position.x,0,places=8)
        self.assertAlmostEqual(n.position.y,0,places=8)

    def test_precision_cancel_and_axis_switch_restore_original_transform(self):
        n=Node3D();n.position=Vector3(.3,.4,0);view=self.view();start=view.project(n.position)
        drag=TransformDrag(n,view,start[:2]);drag.update((start[0]+100,start[1]),precision=True);fine=n.position.x-.3
        drag.update((start[0]+100,start[1]));self.assertAlmostEqual(n.position.x-.3,fine*10)
        drag.set_constraint('Y');drag.update((start[0]+100,start[1]-50));self.assertAlmostEqual(n.position.x,.3)
        drag.cancel();self.assertEqual(n.position,Vector3(.3,.4,0));self.assertFalse(drag.changed)

    def test_rotate_and_scale_are_fps_independent_and_preserve_mirroring(self):
        n=Node3D();n.scale.x=-2;view=self.view();drag=TransformDrag(n,view,(640,360),'scale','X')
        for x in range(640,691):drag.update((x,360))
        self.assertAlmostEqual(n.scale.x,-3);self.assertEqual(n.scale.y,1)
        drag=TransformDrag(n,view,(640,360),'rotate','Z');drag.update((690,360),snap=.5)
        self.assertAlmostEqual(n.rotation.z,math.radians(30))

    def test_ray_picks_actual_triangle_and_parallel_plane_is_safe(self):
        ray=(Vector3(0,0,3),Vector3(0,0,-1))
        self.assertAlmostEqual(triangle_hit(ray,Vector3(-1,-1,0),Vector3(1,-1,0),Vector3(0,1,0)),3)
        self.assertIsNone(plane_hit(ray,Vector3(),Vector3(1,0,0)))

if __name__=='__main__':unittest.main()
