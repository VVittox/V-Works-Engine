




from pathlib import Path
import argparse,json,math,statistics,sys,time
SOURCE=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--engine-root',type=Path,default=SOURCE)
    parser.add_argument('--count',type=int,nargs='+',default=[1000,3000]);parser.add_argument('--repeat',type=int,default=3)
    parser.add_argument('--frames',type=int,default=3);parser.add_argument('--output',type=Path,default=SOURCE/'validation/benchmark.json');args=parser.parse_args()
    sys.path.insert(0,str(SOURCE/'tools'))
    from headless_qt import install
    install()
    from PySide6 import QtGui
    class NullPainter:
        Antialiasing=1
        def __init__(self,*_):pass
        def __getattr__(self,name):return lambda *args,**kwargs:None
    QtGui.QPainter=NullPainter
    sys.path.insert(0,str(args.engine_root.resolve()))
    from engine import __version__
    from engine.scene import Scene,MeshInstance3D,Node3D,Camera3DNode
    from engine.physics import PhysicsWorld,StaticBody3D,RigidBody3D
    from engine.core.settings import PhysicsSettings
    from engine.utils.vmath import Vector3
    from engine.rendering.renderer import PygameRenderer
    from engine.rendering.camera3d import Camera3D
    from editor.widgets.viewport3d import Viewport3D
    class Screen:
        def get_size(self):return (1280,720)
    def scene(count,outside=False):
        root=Scene();cam=Camera3DNode();cam.position=Vector3(0,8,40);root.add_child(cam)
        parent=Node3D();parent.rotation.y=.15;root.add_child(parent);meshes=[]
        for i in range(count):
            n=MeshInstance3D();n.position=Vector3((i%30-14.5)*1.7,1+(i%3)*1.5,-20-(i//30)*1.7)
            if outside and i%10:n.position.x+=1500
            (parent if i%2 else root).add_child(n);meshes.append(n)
        return root,meshes
    def runtime(count,outside):
        root,meshes=scene(count,outside);r=PygameRenderer.__new__(PygameRenderer)
        r.project_root=args.engine_root;r.screen=Screen();r.camera3d=Camera3D();r._mesh3d_cache={};r._triangles3d=[];r._point_lights3d=[];r._spot_lights3d=[]
        def frame():
            r._triangles3d.clear();r.prepare_scene_3d(root)
            for n in meshes:r.queue_mesh_3d(n)
            r._triangles3d.sort(key=lambda t:t[0],reverse=True)
        return frame,lambda:dict(polygons=len(r._triangles3d),**getattr(r,'render_stats',{}))
    def physics(count):
        root=Scene()
        for i in range(count):
            body=RigidBody3D() if i%10==0 else StaticBody3D();body.gravity_scale=0
            body.position=Vector3((i%60)*10,0,(i//60)*10);root.add_child(body)
        world=PhysicsWorld(PhysicsSettings())
        return lambda:world.step(root,1/60),lambda:getattr(world,'stats',{'all_pairs_before_static_filter':count*(count-1)//2})
    def editor(count):
        root,meshes=scene(count,True);v=Viewport3D();v.resize(1280,720);v.set_scene(root);v.distance=45
        return lambda:v.paintEvent(None),lambda:dict(shown=getattr(v,'_shown',None),culled=getattr(v,'_culled',None))
    result={'version':__version__,'engine_root':str(args.engine_root.resolve()),'width':1280,'height':720,
            'repeats':args.repeat,'frames_per_repeat':args.frames,
            'scope':'CPU physics, runtime projection/sort, editor projection with null QPainter. No pixels, SDL, real Qt, sound, input or target-PC FPS.', 'cases':[]}
    for count in args.count:
        for kind,factory in [('physics_sparse',lambda:physics(count)),('runtime_visible',lambda:runtime(count,False)),('runtime_offscreen',lambda:runtime(count,True)),('editor_offscreen',lambda:editor(count))]:
            runs=[]
            for trial in range(args.repeat):
                frame,counters=factory();start=time.perf_counter();frame();cold=(time.perf_counter()-start)*1000
                times=[]
                for _ in range(args.frames):
                    start=time.perf_counter();frame();times.append((time.perf_counter()-start)*1000)
                runs.append(dict(first_ms=round(cold,4),samples_ms=[round(t,4) for t in times],median_ms=round(statistics.median(times),4),counters=counters()))
            row=dict(case=kind,count=count,median_ms=round(statistics.median(r['median_ms'] for r in runs),4),runs=runs)
            result['cases'].append(row);print(f'{__version__}: {count} {kind}: {row["median_ms"]:.3f} ms',flush=True)
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2)+'\n')

if __name__=='__main__':main()
