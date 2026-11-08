
from pathlib import Path
import math,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools.headless_qt import install
install()
from editor.widgets.viewport3d import Viewport3D
from engine.scene import Scene,MeshInstance3D,Node3D
from engine.utils.vmath import Vector3

def main():
    out=ROOT/'validation/previews';out.mkdir(parents=True,exist_ok=True)
    root=Scene();v=Viewport3D();v.set_scene(root);v.target=Vector3(0,1,0);v.distance=16
    for i in range(12):
        n=MeshInstance3D('Architecture');n.position=Vector3((i%4-1.5)*4,.5,(i//4-1)*5);n.size=Vector3(2,1,2);n.color=(84,119,150);root.add_child(n)
    parent=Node3D();parent.rotation=Vector3(0,.55,0);root.add_child(parent)
    hero=MeshInstance3D('Selected');hero.size=Vector3(2,2,2);hero.position=Vector3(0,2,0);parent.add_child(hero);v.select_node(hero)
    for local in (False,True):
        v.local_space=local;v.paintEvent(None);v.image.convert('RGB').save(out/('move_local.png' if local else 'move_world.png'))
    for mode in ('rotate','scale'):
        v.set_gizmo_mode(mode);v.paintEvent(None);v.image.convert('RGB').save(out/(mode+'.png'))
    v.set_gizmo_mode('move');v._refresh_projection();point=v._projection.project(hero.global_position)
    from tools.headless_qt import QPointF,Event
    v._begin_transform(QPointF(*point[:2]),'X');v.mouseMoveEvent(Event(point[0]+80,point[1],modifiers=2));v.paintEvent(None)
    v.image.convert('RGB').save(out/'move_drag.png');v.cancel_transform()
    print('5 Pillow editor previews; no real Qt window was opened.')

if __name__=='__main__':main()
