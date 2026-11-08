from engine.scripting import VScript

class Script(VScript):
    def _process(self, delta):
        self.owner.rotation.y += delta * 0.8
        self.owner.rotation.x += delta * 0.25
