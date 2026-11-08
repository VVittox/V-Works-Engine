


from pathlib import Path
import argparse,sys,types
from PIL import Image,ImageDraw
SOURCE=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser();p.add_argument('--engine-root',type=Path,default=SOURCE);p.add_argument('--output',type=Path,default=SOURCE/'validation/runtime_after');args=p.parse_args()
    sys.path.insert(0,str(args.engine_root.resolve()))
    from engine.scene import Scene,Node3D,MeshInstance3D,Camera3DNode,DirectionalLight3D,PointLight3D,SpotLight3D,WorldEnvironment3D
    from engine.scene.scene_tree import SceneTree
    from engine.rendering.renderer import PygameRenderer
    from engine.rendering.camera3d import Camera3D
    from engine.utils.vmath import Vector3
    class Screen:
        def __init__(self):self.image=Image.new('RGB',(960,540))
        def get_size(self):return self.image.size
        def fill(self,color):self.image.paste(color,(0,0,*self.image.size))
    class Draw:
        @staticmethod
        def polygon(screen,color,points,width):
            if width:ImageDraw.Draw(screen.image).line(points+[points[0]],fill=color,width=width)
            else:ImageDraw.Draw(screen.image).polygon(points,fill=color)
    args.output.mkdir(parents=True,exist_ok=True)
    for case in ('lighting_parent','orthographic','near_side_clip'):
        root=Scene('Render_check');camera=Camera3DNode();camera.position=Vector3(7,5,14);camera.look_at(Vector3(0,1,0));root.add_child(camera)
        environment=WorldEnvironment3D();environment.ambient_color=(218,230,255);environment.ambient_energy=.35
        environment.fog_enabled=True;environment.fog_near=8;environment.fog_far=45;root.add_child(environment)
        sun=DirectionalLight3D();sun.rotation=Vector3(-.7,-.4,.2);root.add_child(sun)
        light=PointLight3D();light.position=Vector3(-3,2,1);light.range=8;root.add_child(light)
        spot=SpotLight3D();spot.position=Vector3(4,4,2);spot.look_at(Vector3(0,0,0));spot.energy=1.8;root.add_child(spot)
        parent=Node3D();parent.position.y=1;parent.rotation=Vector3(.1,.3,-.15);parent.scale=Vector3(1.2,.8,1.1);root.add_child(parent)
        for i,primitive in enumerate(('cube','pyramid','sphere','cylinder')):
            n=MeshInstance3D(primitive,primitive);n.position=Vector3((i-1.5)*2,0,-i%2);n.size=Vector3(1.5,2,1.5)
            n.color=((218,135,91),(100,187,151),(104,146,229),(205,190,104))[i];parent.add_child(n)
        floor=MeshInstance3D('floor','plane');floor.size=Vector3(18,1,18);floor.position.y=-.2;floor.color=(88,101,117);root.add_child(floor)
        if case=='orthographic':camera.orthographic=True;camera.ortho_size=7
        if case=='near_side_clip':
            camera.position=Vector3(0,1.2,0);camera.rotation=Vector3()
            n=MeshInstance3D('Near');n.position=Vector3(.8,1.1,-.4);n.size=Vector3(2,2,2);root.add_child(n)
        renderer=PygameRenderer.__new__(PygameRenderer);renderer.project_root=args.engine_root;renderer.screen=Screen()
        renderer.pygame=types.SimpleNamespace(draw=Draw);renderer.camera3d=Camera3D();renderer._mesh3d_cache={};renderer._triangles3d=[]
        renderer._point_lights3d=[];renderer._spot_lights3d=[]
        tree=SceneTree();tree.set_current_scene(root)

        for _ in range(2):renderer.clear((24,30,45));tree.draw(renderer)
        renderer.screen.image.save(args.output/(case+'.png'))
    print(f'3 runtime Pillow renders -> {args.output}')

if __name__=='__main__':main()
