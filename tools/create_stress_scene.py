
from pathlib import Path
import argparse,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from engine.scene import Scene,MeshInstance3D,Camera3DNode,DirectionalLight3D,WorldEnvironment3D
from engine.physics import StaticBody3D,RigidBody3D
from engine.scene.serialization import save_scene
from engine.utils.vmath import Vector3

def main():
    p=argparse.ArgumentParser();p.add_argument('--count',type=int,default=1000);p.add_argument('--output',type=Path);args=p.parse_args()
    count=max(1,min(10000,args.count));out=args.output or ROOT/f'project/scenes/performance_{count}.vscene'
    scene=Scene(f'Performance_{count}',(28,33,43));camera=Camera3DNode();camera.position=Vector3(42,38,48);camera.look_at(Vector3(0,0,-35));scene.add_child(camera)
    light=DirectionalLight3D();light.rotation=Vector3(-.7,-.4,0);scene.add_child(light)
    environment=WorldEnvironment3D();environment.ambient_energy=.5;scene.add_child(environment)
    length=max(60,(count//40+3)*3);floor=StaticBody3D('Floor');floor.position=Vector3(0,-.2,-length*.5)
    floor.collider.size=Vector3(140,.4,length+20);scene.add_child(floor)
    mesh=MeshInstance3D('Ground');mesh.size=floor.collider.size;mesh.color=(75,88,105);mesh.double_sided=False;floor.add_child(mesh)
    for i in range(count):
        moving=i%20==0;body=RigidBody3D(f'Dynamic_{i:04d}') if moving else StaticBody3D(f'Static_{i:04d}')
        body.position=Vector3((i%40-19.5)*3,4 if moving else .9,-(i//40+2)*3);body.collider.size=Vector3(1.8,1.8,1.8)
        mesh=MeshInstance3D('Mesh');mesh.size=Vector3(1.8,1.8,1.8);mesh.double_sided=False
        mesh.color=(224,162,91) if moving else (82+i%5*15,128,170);body.add_child(mesh);scene.add_child(body)
    out.parent.mkdir(parents=True,exist_ok=True);save_scene(scene,out)
    print(f'{count} props; {sum(1 for _ in scene.walk())} nodes -> {out}')

if __name__=='__main__':main()
