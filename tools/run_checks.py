
from pathlib import Path
import importlib.util,inspect,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

class MonkeyPatch:
    def __init__(self):self.undo=[]
    def setattr(self,obj,name,value,raising=True):
        exists=hasattr(obj,name)
        if raising and not exists:raise AttributeError(name)
        self.undo.append((obj,name,exists,getattr(obj,name,None)));setattr(obj,name,value)
    def restore(self):
        for obj,name,exists,value in reversed(self.undo):
            if exists:setattr(obj,name,value)
            else:delattr(obj,name)

def main():
    scratch=ROOT/'.checks_tmp';scratch.mkdir(exist_ok=True)
    spec=importlib.util.spec_from_file_location('original_core_tests',ROOT/'tests/test_core.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    suite=unittest.TestSuite()
    for name,fn in inspect.getmembers(module,inspect.isfunction):
        if not name.startswith('test_'):continue
        def run(fn=fn):
            patch=MonkeyPatch()
            with tempfile.TemporaryDirectory(dir=scratch) as temp:
                values={'tmp_path':Path(temp),'monkeypatch':patch}
                try:fn(**{key:values[key] for key in inspect.signature(fn).parameters})
                finally:patch.restore()
        suite.addTest(unittest.FunctionTestCase(run,description=name))
    for pattern in ('test_performance.py','test_gizmo.py','test_viewport.py'):
        suite.addTests(unittest.defaultTestLoader.discover(str(ROOT/'tests'),pattern=pattern))
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1

if __name__=='__main__':raise SystemExit(main())
