from engine.scripting import VScript

class Script(VScript):

    def __init__(self, owner):
        super().__init__(owner)
        self.flip = False

    def on_timeout(self):
        self.flip = not self.flip
        self.owner.color = (120, 220, 255, 255) if self.flip else (160, 195, 235, 255)
