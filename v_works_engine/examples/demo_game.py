from engine import Engine, EngineSettings, Scene, Node2D, Vector2
from engine.ui import UILabel

class Player(Node2D):

    def __init__(self) -> None:
        super().__init__('Player')
        self.position = Vector2(100, 280)
        self.size = Vector2(48, 48)
        self.speed = 260.0

    def _process(self, delta: float) -> None:
        engine = self.get_tree().engine
        direction = engine.input.get_vector('ui_left', 'ui_right', 'ui_up', 'ui_down')
        self.position += direction * self.speed * delta
        viewport = engine.renderer.size
        self.position.x = max(0, min(viewport.x - self.size.x, self.position.x))
        self.position.y = max(0, min(viewport.y - self.size.y, self.position.y))

    def _draw(self, renderer) -> None:
        renderer.draw_rect(self.global_position, self.size, (86, 210, 255))
        renderer.draw_rect(self.global_position, self.size, (230, 250, 255), width=2)

class DemoScene(Scene):

    def __init__(self) -> None:
        super().__init__('DemoScene', background_color=(17, 20, 28))
        self.add_child(Player())

    def _draw(self, renderer) -> None:
        renderer.draw_circle(Vector2(640, 360), 90, (36, 46, 66))
        renderer.draw_circle(Vector2(640, 360), 90, (80, 100, 140), width=3)
if __name__ == '__main__':
    settings = EngineSettings()
    settings.window.title = 'V Works Engine — Demo'
    settings.window.width = 960
    settings.window.height = 540
    settings.target_fps = 120
    engine = Engine(settings)
    engine.ui.add_label(UILabel('V Works Engine 0.1 — WASD / Arrows, ESC to quit', Vector2(18, 16), 20))
    engine.run(DemoScene())
