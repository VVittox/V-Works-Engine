
from __future__ import annotations
import io
import json
import zipfile
from .advanced_nodes import Control
from ..utils.vmath import Vector2


class UICanvas(Control):
    def __init__(self, name='UICanvas'):
        super().__init__(name)
        self.reference_size = Vector2(1920,1080)

    def layout_scale(self, viewport):
        return min(viewport.x/max(1,self.reference_size.x), viewport.y/max(1,self.reference_size.y))

    def resolved_rect(self, viewport):
        scale = self.layout_scale(viewport)
        size = self.reference_size*scale
        return (viewport-size)*0.5, size


def ui_scale(node, viewport):
    while node is not None:
        if isinstance(node, UICanvas):
            return node.layout_scale(viewport)
        node = node.parent
    return 1.0


class UIImage(Control):
    def __init__(self, name='UIImage'):
        super().__init__(name)
        self.texture_path = ''
        self.color = (255,255,255,255)
        self.fill_amount = 1.0
        self.preserve_aspect = False
        self.pixel_perfect = True

    def _draw(self, renderer):
        pos,size = self.resolved_rect(renderer.size)
        size.x *= max(0,min(1,self.fill_amount))
        if size.x <= 0 or size.y <= 0: return
        if self.texture_path:
            renderer.draw_image_rect(self.texture_path,pos,size,tint=self.color,
                                     preserve_aspect=self.preserve_aspect,
                                     pixel_perfect=self.pixel_perfect,rotation=self.rotation)
        elif self.color[3] > 0:
            renderer.draw_rect_alpha(pos,size,self.color,world=False)


class UIButton(UIImage):
    def __init__(self,name='UIButton'):
        super().__init__(name)
        self.text = ''
        self.font_path = ''
        self.font_size = 24
        self.text_color = (255,255,255,255)
        self.disabled = False
        self.focused = False
        self._hovered = False
        self._held = set()
        self.signals.add('pressed')

    def _process(self,delta):
        tree=self.get_tree(); engine=tree.engine if tree else None
        if engine is None or engine.input is None or engine.renderer is None: return
        if not self.is_visible_in_tree or self.disabled:
            self._held.clear(); return
        pos,size=self.resolved_rect(engine.renderer.size)
        def inside(p): return pos.x <= p.x < pos.x+size.x and pos.y <= p.y < pos.y+size.y
        inp=engine.input
        self._hovered=inside(inp.mouse_position)
        for ident,p in inp.pointer_pressed:
            if inside(p): self._held.add(ident)
        for ident,p in inp.pointer_released:
            if ident in self._held:
                self._held.remove(ident)
                if inside(p): self.signals.emit('pressed')

    def _draw(self,renderer):
        super()._draw(renderer)
        pos,size=self.resolved_rect(renderer.size)
        if self.disabled:
            renderer.draw_rect_alpha(pos,size,(10,10,14,125),world=False)
        elif self._hovered or self.focused:
            renderer.draw_rect_alpha(pos,size,(255,245,210,45),world=False)
            renderer.draw_rect(pos,size,(255,210,80),max(1,round(ui_scale(self,renderer.size)*3)),world=False)
        if self.text:
            renderer.draw_ui_text(self.text,pos,size,self.font_size*ui_scale(self,renderer.size),
                                  self.text_color,self.font_path,'center','center')


class VideoPlayer(Control):





    def __init__(self,name='VideoPlayer'):
        super().__init__(name)
        self.clip_path=''
        self.autoplay=True
        self.loop=False
        self.volume=1.0
        self.playing=False
        self.elapsed=0.0
        self._archive=None
        self._manifest={}
        self._frame=None
        self._frame_number=-1
        self._channel=None
        self.signals.add('finished')
        self.signals.connect('exit_tree',self.stop)

    def play(self):
        tree=self.get_tree(); engine=tree.engine if tree else None
        if not self.clip_path or engine is None or engine.renderer is None: return
        if self._archive is None:
            self._archive=zipfile.ZipFile(engine.project_root/self.clip_path)
            self._manifest=json.loads(self._archive.read('manifest.json'))
        self.elapsed=0.0; self.playing=True
        audio=self._manifest.get('audio','')
        if audio and engine.audio is not None:
            self._channel=engine.audio.play(str(engine.project_root/audio),loops=-1 if self.loop else 0,volume=self.volume)

    def stop(self):
        self.playing=False
        if self._channel is not None: self._channel.stop()
        self._channel=None
        if self._archive is not None: self._archive.close()
        self._archive=None; self._frame=None; self._frame_number=-1

    def _process(self,delta):
        if self._archive is None and self.autoplay: self.play()
        if not self.playing: return
        self.elapsed+=max(0,delta)
        duration=float(self._manifest.get('duration',1))
        if self.elapsed >= duration:
            if self.loop: self.elapsed %= duration
            else:
                self.playing=False
                self.signals.emit('finished')
                self.elapsed=max(0,duration-1/float(self._manifest.get('fps',30)))

    def _draw(self,renderer):
        if self._archive is None: return
        count=int(self._manifest['frames']); fps=float(self._manifest['fps'])
        number=min(count-1,max(0,int(self.elapsed*fps)))
        number-=number%max(1,int(getattr(self,'frame_stride',1)))
        if number != self._frame_number:
            raw=self._archive.read(f'frames/{number:06d}.jpg')
            self._frame=renderer.pygame.image.load(io.BytesIO(raw),'frame.jpg').convert()
            self._frame_number=number
        if self._frame is not None:
            pos,size=self.resolved_rect(renderer.size)
            renderer.draw_surface_rect(self._frame,pos,size,preserve_aspect=True)
