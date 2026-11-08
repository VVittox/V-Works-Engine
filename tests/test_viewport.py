
from pathlib import Path
import ast,json,math,sys,unittest
from tools.headless_qt import install,Event,Qt,QPointF
install()
from editor.widgets.viewport3d import Viewport3D
from editor.scene_document import SceneDocument
from engine.scene import Scene,MeshInstance3D,Node3D
from engine.scene.serialization import node_to_dict
from engine.utils.vmath import Vector3

class ViewportTests(unittest.TestCase):
    def viewport(self):
        v=Viewport3D();root=Scene();node=MeshInstance3D();root.add_child(node);v.set_scene(root);v.select_node(node);v._refresh_projection()
        return v,node

    def test_select_surface_far_from_pivot_and_hidden_parent_is_not_picked(self):
        v,n=self.viewport();n.size=Vector3(6,6,6);p=v._projection.project(Vector3(2,0,3))
        self.assertIs(v._hit_test(QPointF(*p[:2])),n)
        parent=Node3D();v.scene_root.add_child(parent);parent.add_child(n);parent.visible=False
        self.assertIsNone(v._hit_test(QPointF(*p[:2])))

    def test_handle_drag_is_one_transaction_and_escape_restores_transform(self):
        v,n=self.viewport();p=v._projection.project(n.global_position);v._begin_transform(QPointF(*p[:2]),'X')
        for i in range(1,31):v.mouseMoveEvent(Event(p[0]+i*2,p[1]))
        self.assertGreater(n.position.x,0);self.assertEqual(len(v.transform_started.calls),1)
        self.assertEqual(len(v.transform_finished.calls),0)
        v.keyPressEvent(Event(key=Qt.Key_Escape));self.assertEqual(n.position,Vector3())
        self.assertEqual(v.transform_finished.calls,[(n,False)])

    def test_click_select_does_not_accidentally_move_and_locked_nodes_stay_put(self):
        v,n=self.viewport();v.select_node(None);p=v._projection.project(n.global_position)
        v.mousePressEvent(Event(p[0],p[1]));v.mouseMoveEvent(Event(p[0]+30,p[1]+30));v.mouseReleaseEvent(Event())
        self.assertIs(v.selected,n);self.assertEqual(n.position,Vector3())
        n.editor_locked=True;v._begin_transform(QPointF(*p[:2]));self.assertIsNone(v._drag)

    def test_frame_size_and_all_gizmo_modes_paint(self):
        v,n=self.viewport();n.size=Vector3(12,8,10);v.frame_selected();large=v.distance
        n.size=Vector3(1,1,1);v.frame_selected();self.assertLess(v.distance,large)
        for mode in ('move','rotate','scale'):
            v.set_gizmo_mode(mode);v.paintEvent(None);self.assertEqual(v.image.size,(1280,720));self.assertTrue(v._gizmo_handles)

    def test_focus_loss_and_scene_change_cancel_without_an_undo_entry(self):
        for operation in ('focus','scene'):
            v,n=self.viewport();p=v._projection.project(n.global_position);v._begin_transform(QPointF(*p[:2]));v.mouseMoveEvent(Event(p[0]+40,p[1]+40))
            if operation=='focus':v.focusOutEvent(Event())
            else:v.set_scene(Scene())
            self.assertEqual(n.position,Vector3());self.assertEqual(v.transform_finished.calls[-1],(n,False))

    def test_axis_shortcut_restricts_an_existing_move_immediately(self):
        v,n=self.viewport();p=v._projection.project(n.global_position);v._begin_transform(QPointF(*p[:2]))
        v.mouseMoveEvent(Event(p[0]+50,p[1]-40));self.assertGreater(n.position.y,0)
        v.keyPressEvent(Event(key=Qt.Key_X));self.assertAlmostEqual(n.position.y,0);self.assertAlmostEqual(n.position.z,0)
        v.mouseReleaseEvent(Event());self.assertEqual(v.transform_finished.calls[-1],(n,True))

    def test_g_move_confirms_on_click_without_changing_selection(self):
        v,n=self.viewport();p=v._projection.project(n.global_position);v._last=QPointF(*p[:2]);v.keyPressEvent(Event(key=Qt.Key_G))
        v.mouseMoveEvent(Event(p[0]+40,p[1]));v.mousePressEvent(Event(p[0]+40,p[1]))
        self.assertIsNone(v._drag);self.assertIs(v.selected,n);self.assertEqual(v.transform_finished.calls[-1],(n,True))

class HistoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):


        source=ast.parse((Path(__file__).parents[1]/'editor/main_window.py').read_text())
        window=next(n for n in source.body if isinstance(n,ast.ClassDef) and n.name=='MainWindow')
        names={'_snapshot','_ensure_history','_commit_history','_begin_transform','_transform_preview','_end_transform'}
        methods=[n for n in window.body if isinstance(n,ast.FunctionDef) and n.name in names]
        module=ast.Module(body=[ast.ClassDef(name='Methods',bases=[],keywords=[],body=methods,decorator_list=[])],type_ignores=[])
        context={'SceneDocument':SceneDocument,'Node':Node3D,'json':json,'node_to_dict':node_to_dict}
        exec(compile(ast.fix_missing_locations(module),'<actual editor history methods>','exec'),context)
        cls.methods=context['Methods']

    def editor(self):
        from types import SimpleNamespace
        editor=self.methods();editor.document=SceneDocument(Scene());n=MeshInstance3D();editor.document.scene.add_child(n)
        editor._history={};editor.viewport=SimpleNamespace(update=lambda:None);editor.inspector=SimpleNamespace(set_node=lambda n:None)
        editor._refresh_diagnostics=lambda:None;editor._update_title=lambda:None
        real=editor._snapshot;editor.snapshot_count=0
        def snapshot(doc=None):editor.snapshot_count+=1;return real(doc)
        editor._snapshot=snapshot;editor._ensure_history(editor.document);return editor,n

    def test_hundred_drag_events_serialize_scene_once_at_commit_and_undo_atomically(self):
        e,n=self.editor();before=e._snapshot();count=e.snapshot_count;e._begin_transform(n)
        for i in range(100):n.position.x=i*.1;e._transform_preview(n)
        self.assertEqual(e.snapshot_count,count);e._end_transform(n,True);self.assertEqual(e.snapshot_count,count+1)
        history=e._history[id(e.document)];self.assertEqual(history['undo'],[before])
        self.assertNotEqual(history['last'],before);self.assertTrue(e.document.dirty)

    def test_cancel_preserves_history_and_dirty_flag(self):
        e,n=self.editor();history=e._ensure_history(e.document);e._begin_transform(n);n.position.x=5;e._transform_preview(n)
        n.position.x=0;e._end_transform(n,False)
        self.assertFalse(e.document.dirty);self.assertEqual(history['undo'],[])
        self.assertEqual(json.loads(e._ensure_history(e.document)['last']),json.loads(e._snapshot()))

if __name__=='__main__':unittest.main()
