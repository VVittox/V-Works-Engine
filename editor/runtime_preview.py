




from engine.core.engine import Engine
from engine.runtime_game import settings_from_project, _load_runtime_scene
from engine.scene.serialization import node_from_dict, node_to_dict
from engine.scripting import attach_project_scripts, connect_scene_signals


class RuntimePreview:
    def __init__(self, project):
        self.project = project
        settings = settings_from_project(project)
        settings.custom['offscreen'] = True
        self.engine = Engine(settings)
        self.engine.scene_loader = lambda request: _load_runtime_scene(project, request)
        self.events = []

    def start(self, source):
        self.engine.start()
        if self.engine.input is not None:self.engine.input.poll_mouse=False
        scene = node_from_dict(node_to_dict(source))
        attach_project_scripts(scene, self.project.root, strict=self.project.runtime.strict_scripts)
        connect_scene_signals(scene, strict=self.project.runtime.strict_scripts)
        self.engine.set_scene(scene)
        self.engine.running = True

    def event(self, kind, **values):
        self.events.append(self.engine.renderer.pygame.event.Event(kind, values))

    def advance(self, delta, *, poll_devices=True, render=True):
        events, self.events = self.events, []
        if poll_devices:
            pg = self.engine.renderer.pygame


            device_types = {getattr(pg, key, -100) for key in (
                'JOYDEVICEADDED', 'JOYDEVICEREMOVED', 'JOYAXISMOTION',
                'JOYBUTTONDOWN', 'JOYBUTTONUP')}
            events.extend(event for event in pg.event.get() if event.type in device_types)
        self.engine.advance_frame(delta, events, render=render)

    def stop(self):
        self.events.clear()
        self.engine.shutdown()
