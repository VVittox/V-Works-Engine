from __future__ import annotations
from pathlib import Path
from typing import Dict, Iterable, Tuple
import json
import math
import logging
from collections import OrderedDict
from ..utils.vmath import Vector2, Vector3
from .camera import Camera2D
from .camera3d import Camera3D
from .mesh3d import Mesh3D
from .texture import Texture
from .cache3d import GeometryCache3D
from .projection3d import Projection3D, visible_nodes

class PygameRenderer:

    def __init__(self, window_settings, project_root: str | Path | None=None, *, offscreen: bool=False, render_backend: str='cpu') -> None:
        try:
            import pygame
        except ImportError as exc:
            raise RuntimeError('Pygame is required. Install with: pip install -r requirements.txt') from exc
        self.pygame = pygame
        self.offscreen = offscreen
        self.project_root = Path(project_root).resolve() if project_root else Path.cwd().resolve()
        pygame.init()
        flags = 0
        if window_settings.fullscreen:
            flags |= pygame.FULLSCREEN
        if window_settings.borderless:
            flags |= pygame.NOFRAME
        if window_settings.resizable:
            flags |= pygame.RESIZABLE
        size = (window_settings.width, window_settings.height)
        if offscreen:


            pygame.display.set_mode((1, 1), pygame.HIDDEN)
            self.screen = pygame.Surface(size).convert()
        else:
            try:
                self.screen = pygame.display.set_mode(size, flags, vsync=1 if window_settings.vsync else 0)
            except (TypeError, pygame.error):
                self.screen = pygame.display.set_mode(size, flags)
        pygame.display.set_caption(window_settings.title)
        if window_settings.window_icon:
            try:
                pygame.display.set_icon(pygame.image.load(window_settings.window_icon))
            except (pygame.error, FileNotFoundError):
                pass
        self.camera = Camera2D()
        self.camera3d = Camera3D()
        self._triangles3d: list[tuple[float, list[tuple[int, int]], tuple[int, int, int], bool]] = []
        self._mesh3d_cache: Dict[tuple, Mesh3D] = {}
        self._light3d_direction = Vector3(-0.4, -1.0, -0.6).normalized
        self._light3d_color = (255, 244, 220)
        self._light3d_energy = 1.0
        self._ambient3d_color = (255, 255, 255)
        self._ambient3d_energy = 0.22
        self._fog3d_enabled = False
        self._fog3d_color = (100, 120, 145)
        self._fog3d_near = 20.0
        self._fog3d_far = 100.0
        self._sky3d_enabled = False
        self._sky3d_top_color = (35, 50, 82)
        self._sky3d_bottom_color = (145, 185, 225)
        self._point_lights3d: list[dict] = []
        self._spot_lights3d: list[dict] = []
        self._font_cache: Dict[Tuple[str, int], object] = {}
        self._image_cache: Dict[str, object] = {}
        self._resource_cache: Dict[str, dict] = {}
        self._geometry3d = GeometryCache3D()
        self._view3d = None
        self._sprite_cache = OrderedDict()
        self._sprite_cache_bytes = 0
        self._sprite_cache_budget = 64 * 1024 * 1024
        self._text_cache = OrderedDict()
        self._text_cache_bytes = 0
        self.stats_2d = {'drawn':0,'culled':0,'cache_hits':0}
        self.render_stats = {'meshes':0,'culled':0,'faces':0}
        self.requested_3d_backend = str(render_backend).lower()
        self.active_3d_backend = 'cpu'
        self._gpu3d = None
        if self.requested_3d_backend in ('gpu', 'auto'):
            try:
                from .gpu3d import GpuTriangles3D
                self._gpu3d = GpuTriangles3D()
                self.active_3d_backend = 'gpu (OpenGL 3.3, readback)'
            except Exception as exc:
                logging.getLogger('VWorks.renderer').warning(
                    'GPU 3D unavailable; falling back to CPU: %s', exc
                )

    @property
    def size(self) -> Vector2:
        w, h = self.screen.get_size()
        return Vector2(float(w), float(h))

    def resolve_asset(self, path: str | Path) -> str:
        if not path:
            return ''
        p = Path(path)
        if not p.is_absolute():
            p = self.project_root / p
        return str(p.resolve())

    def _point(self, p: Vector2, world: bool=True) -> Tuple[int, int]:
        q = self.camera.world_to_screen(p, self.size) if world else p
        return (int(round(q.x)), int(round(q.y)))

    def clear(self, color: Tuple[int, int, int]) -> None:
        self._triangles3d.clear()
        if getattr(self, '_gpu3d', None) is not None: self._gpu3d.clear()
        self.screen.fill(color)
        self.stats_2d = {'drawn':0,'culled':0,'cache_hits':0}

    def present(self) -> None:
        if not self.offscreen:
            self.pygame.display.flip()

    def draw_rect(self, position: Vector2, size: Vector2, color=(255, 255, 255), width: int=0, world: bool=True) -> None:
        p = self.camera.world_to_screen(position, self.size) if world else position
        z = self.camera.zoom if world and self.camera.enabled else 1.0
        rect = self.pygame.Rect(round(p.x), round(p.y), round(size.x * z), round(size.y * z))
        self.pygame.draw.rect(self.screen, color, rect, width)

    def draw_circle(self, position: Vector2, radius: float, color=(255, 255, 255), width: int=0, world: bool=True) -> None:
        z = self.camera.zoom if world and self.camera.enabled else 1.0
        self.pygame.draw.circle(self.screen, color, self._point(position, world), max(1, round(radius * z)), width)

    def draw_rect_alpha(self, position: Vector2, size: Vector2, color=(255, 255, 255, 128), world: bool=True) -> None:
        p = self.camera.world_to_screen(position, self.size) if world else position
        z = self.camera.zoom if world and self.camera.enabled else 1.0
        w, h = (max(1, round(size.x * z)), max(1, round(size.y * z)))
        surf = self.pygame.Surface((w, h), self.pygame.SRCALPHA)
        surf.fill(tuple(color))
        self.screen.blit(surf, (round(p.x), round(p.y)))

    def draw_circle_alpha(self, position: Vector2, radius: float, color=(255, 255, 255, 128), world: bool=True) -> None:
        z = self.camera.zoom if world and self.camera.enabled else 1.0
        r = max(1, round(radius * z))
        surf = self.pygame.Surface((r * 2 + 2, r * 2 + 2), self.pygame.SRCALPHA)
        self.pygame.draw.circle(surf, tuple(color), (r + 1, r + 1), r)
        point = self._point(position, world)
        self.screen.blit(surf, (point[0] - r - 1, point[1] - r - 1))

    def draw_light(self, position: Vector2, radius: float, color=(255, 230, 180), energy: float=1.0, softness: float=0.7) -> None:
        z = self.camera.zoom if self.camera.enabled else 1.0
        r = max(2, round(radius * z))
        surf = self.pygame.Surface((r * 2, r * 2), self.pygame.SRCALPHA)
        rings = max(8, min(64, round(16 + softness * 32)))
        for i in range(rings, 0, -1):
            t = i / rings
            rr = max(1, round(r * t))
            alpha = max(0, min(255, round(255 * energy * (1 - t) * 0.22)))
            self.pygame.draw.circle(surf, (*color[:3], alpha), (r, r), rr)
        point = self._point(position, True)
        self.screen.blit(surf, (point[0] - r, point[1] - r), special_flags=self.pygame.BLEND_RGBA_ADD)

    def draw_screen_modulate(self, color=(255, 255, 255, 255)) -> None:
        overlay = self.pygame.Surface(self.screen.get_size(), self.pygame.SRCALPHA)
        overlay.fill(tuple(color))
        self.screen.blit(overlay, (0, 0), special_flags=self.pygame.BLEND_RGBA_MULT)

    def draw_line(self, a: Vector2, b: Vector2, color=(255, 255, 255), width: int=1, world: bool=True) -> None:
        self.pygame.draw.line(self.screen, color, self._point(a, world), self._point(b, world), width)

    def draw_polygon(self, points: Iterable[Vector2], color=(255, 255, 255), width: int=0, world: bool=True) -> None:
        self.pygame.draw.polygon(self.screen, color, [self._point(p, world) for p in points], width)

    def draw_texture(self, texture: Texture, position: Vector2, world: bool=True) -> None:
        p = self.camera.world_to_screen(position, self.size) if world else position
        surface = texture.surface
        if world and self.camera.enabled and (self.camera.zoom != 1.0):
            w = max(1, round(texture.width * self.camera.zoom))
            h = max(1, round(texture.height * self.camera.zoom))
            surface = self.pygame.transform.smoothscale(surface, (w, h))
        self.screen.blit(surface, (round(p.x), round(p.y)))

    def _image(self, path: str):
        resolved = self.resolve_asset(path)
        surface = self._image_cache.get(resolved)
        if surface is None:
            surface = self.pygame.image.load(resolved).convert_alpha()
            self._image_cache[resolved] = surface
        return surface

    def _resource_data(self, path: str) -> dict:
        if not path:
            return {}
        resolved = self.resolve_asset(path)
        if resolved not in self._resource_cache:
            try:
                payload = json.loads(Path(resolved).read_text(encoding='utf-8'))
                self._resource_cache[resolved] = dict(payload.get('data', {})) if payload.get('format') == 'vworks_resource' else {}
            except Exception:
                self._resource_cache[resolved] = {}
        return self._resource_cache[resolved]

    def _apply_material(self, surface, material_path: str):
        data = self._resource_data(material_path)
        if not data:
            return (surface, 'alpha')
        result = surface.copy()
        preset = str(data.get('shader_preset', data.get('preset', 'none'))).lower()
        shader_path = str(data.get('shader', '') or '')
        if shader_path:
            shader = self._resource_data(shader_path)
            preset = str(shader.get('preset', preset)).lower()
        if preset == 'grayscale' and hasattr(self.pygame.transform, 'grayscale'):
            result = self.pygame.transform.grayscale(result)
        elif preset == 'invert':
            inv = self.pygame.Surface(result.get_size(), self.pygame.SRCALPHA)
            inv.fill((255, 255, 255, 255))
            inv.blit(result, (0, 0), special_flags=self.pygame.BLEND_RGB_SUB)
            result = inv
        elif preset == 'pixelate':
            px = max(1, int(dict(data.get('params', {})).get('pixel_size', 4)))
            w = max(1, result.get_width() // px)
            h = max(1, result.get_height() // px)
            result = self.pygame.transform.scale(self.pygame.transform.scale(result, (w, h)), result.get_size())
        tint = list(data.get('tint', [255, 255, 255, 255]))
        tint = (tint + [255] * 4)[:4]
        if tuple(tint) != (255, 255, 255, 255):
            result.fill(tuple(tint), special_flags=self.pygame.BLEND_RGBA_MULT)
        return (result, str(data.get('blend_mode', 'alpha')).lower())

    def draw_atlas_tile(self, path: str, tile_index: int, columns: int, tile_size: Vector2, position: Vector2, scale: Vector2 | None=None, margin: int=0, spacing: int=0, world: bool=True) -> None:
        try:
            source = self._image(path)
        except (FileNotFoundError, self.pygame.error):
            self.draw_rect(position, tile_size, (220, 70, 110), 2, world)
            return
        tw, th = (max(1, int(tile_size.x)), max(1, int(tile_size.y)))
        cols = max(1, int(columns))
        idx = max(0, int(tile_index))
        col = idx % cols
        row = idx // cols
        x = margin + col * (tw + spacing)
        y = margin + row * (th + spacing)
        if x + tw > source.get_width() or y + th > source.get_height():
            self.draw_rect(position, tile_size, (220, 70, 110), 2, world)
            return
        surf = source.subsurface(self.pygame.Rect(x, y, tw, th)).copy()
        scale = scale or Vector2(1, 1)
        cam = self.camera.zoom if world and self.camera.enabled else 1.0
        target = (max(1, round(tw * abs(scale.x) * cam)), max(1, round(th * abs(scale.y) * cam)))
        if target != surf.get_size():
            surf = self.pygame.transform.scale(surf, target)
        p = self.camera.world_to_screen(position, self.size) if world else position
        self.screen.blit(surf, (round(p.x), round(p.y)))

    def draw_image_path(self, path: str, position: Vector2, scale: Vector2 | None=None, rotation: float=0.0, centered: bool=True, flip_h: bool=False, flip_v: bool=False, opacity: float=1.0, world: bool=True, material_path: str='', tint=(255,255,255,255), pixel_perfect: bool=False) -> None:
        try:
            surface = self._image(path)
        except (FileNotFoundError, self.pygame.error):
            self.draw_rect(position, Vector2(48, 48), (220, 70, 110), 2, world)
            self.draw_line(position, position + Vector2(48, 48), (220, 70, 110), 2, world)
            return
        scale = scale or Vector2(1, 1)
        cam_zoom = self.camera.zoom if world and self.camera.enabled else 1.0
        sx, sy = (abs(scale.x) * cam_zoom, abs(scale.y) * cam_zoom)
        target = (max(1, round(surface.get_width() * sx)), max(1, round(surface.get_height() * sy)))
        p = self.camera.world_to_screen(position, self.size) if world else position
        rw = abs(math.cos(rotation))*target[0]+abs(math.sin(rotation))*target[1]
        rh = abs(math.sin(rotation))*target[0]+abs(math.cos(rotation))*target[1]
        bound = self.pygame.Rect(round(p.x-rw*.5 if centered else p.x),round(p.y-rh*.5 if centered else p.y),math.ceil(rw),math.ceil(rh))
        if not bound.colliderect(self.screen.get_rect()) or opacity <= 0:
            self.stats_2d['culled'] += 1
            return
        self.stats_2d['drawn'] += 1
        fh = flip_h ^ (scale.x < 0)
        fv = flip_v ^ (scale.y < 0)
        if max(target) > 4096 and abs(rotation) < 1e-9:
            if fh or fv: surface=self.pygame.transform.flip(surface,fh,fv)
            if material_path: surface,_=self._apply_material(surface,material_path)
            if tuple(tint)!=(255,255,255,255):
                surface=surface.copy();surface.fill(tuple(tint),special_flags=self.pygame.BLEND_RGBA_MULT)
            if opacity < .999: surface=surface.copy();surface.set_alpha(round(opacity*255))
            origin=p-Vector2(*target)*.5 if centered else p
            self.draw_surface_rect(surface,origin,Vector2(*target),pixel_perfect=pixel_perfect)
            return
        key=(self.resolve_asset(path),target,round(rotation,5),fh,fv,material_path,tuple(tint),round(opacity*255),pixel_perfect)
        entry=self._sprite_cache.get(key)
        if entry is not None:
            surface,blend_mode=entry
            self._sprite_cache.move_to_end(key)
            self.stats_2d['cache_hits']+=1
            rect=surface.get_rect()
            if centered: rect.center=(round(p.x),round(p.y))
            else: rect.topleft=(round(p.x),round(p.y))
            flags=self.pygame.BLEND_RGBA_ADD if blend_mode=='add' else self.pygame.BLEND_RGBA_MULT if blend_mode=='multiply' else 0
            self.screen.blit(surface,rect,special_flags=flags)
            return
        if target != surface.get_size():
            transform=self.pygame.transform.scale if pixel_perfect else self.pygame.transform.smoothscale
            surface = transform(surface, target)
        if fh or fv:
            surface = self.pygame.transform.flip(surface, fh, fv)
        if rotation:
            surface = self.pygame.transform.rotate(surface, -rotation * 57.29577951308232)
        blend_mode = 'alpha'
        if material_path:
            surface, blend_mode = self._apply_material(surface, material_path)
        if tuple(tint)!=(255,255,255,255):
            surface=surface.copy()
            surface.fill(tuple(tint),special_flags=self.pygame.BLEND_RGBA_MULT)
        if opacity < 0.999:
            surface = surface.copy()
            surface.set_alpha(max(0, min(255, round(opacity * 255))))
        p = self.camera.world_to_screen(position, self.size) if world else position
        rect = surface.get_rect()
        if centered:
            rect.center = (round(p.x), round(p.y))
        else:
            rect.topleft = (round(p.x), round(p.y))
        flags = self.pygame.BLEND_RGBA_ADD if blend_mode == 'add' else self.pygame.BLEND_RGBA_MULT if blend_mode == 'multiply' else 0
        self.screen.blit(surface, rect, special_flags=flags)
        cost=surface.get_width()*surface.get_height()*4
        if cost <= self._sprite_cache_budget//4:
            self._sprite_cache[key]=(surface,blend_mode);self._sprite_cache_bytes+=cost
            while self._sprite_cache_bytes>self._sprite_cache_budget:
                _,(old,_)=self._sprite_cache.popitem(last=False)
                self._sprite_cache_bytes-=old.get_width()*old.get_height()*4

    def draw_surface_rect(self,surface,position,size,preserve_aspect=False,pixel_perfect=False):
        if size.x<=0 or size.y<=0: return
        pg=self.pygame
        target=Vector2(size.x,size.y)
        if preserve_aspect:
            factor=min(size.x/surface.get_width(),size.y/surface.get_height())
            target=Vector2(surface.get_width()*factor,surface.get_height()*factor)
            position=position+(size-target)*.5
        dst=pg.Rect(round(position.x),round(position.y),max(1,round(target.x)),max(1,round(target.y)))
        clipped=dst.clip(self.screen.get_rect())
        if clipped.width<=0 or clipped.height<=0: return
        transform=pg.transform.scale if pixel_perfect else pg.transform.smoothscale
        if max(dst.size)>4096:
            sw,sh=surface.get_size()
            x1=max(0,math.floor((clipped.left-dst.left)*sw/dst.width))
            y1=max(0,math.floor((clipped.top-dst.top)*sh/dst.height))
            x2=min(sw,math.ceil((clipped.right-dst.left)*sw/dst.width))
            y2=min(sh,math.ceil((clipped.bottom-dst.top)*sh/dst.height))
            crop=surface.subsurface((x1,y1,max(1,x2-x1),max(1,y2-y1)))
            origin=(round(dst.left+x1*dst.width/sw),round(dst.top+y1*dst.height/sh))
            outsize=(max(1,round((x2-x1)*dst.width/sw)),max(1,round((y2-y1)*dst.height/sh)))
            self.screen.blit(transform(crop,outsize),origin)
        else:
            self.screen.blit(transform(surface,dst.size),dst)

    def draw_image_rect(self,path,position,size,tint=(255,255,255,255),preserve_aspect=False,pixel_perfect=False,rotation=0.0):
        source=self._image(path)
        if preserve_aspect:
            factor=min(size.x/source.get_width(),size.y/source.get_height())
            actual=Vector2(source.get_width()*factor,source.get_height()*factor)
            position=position+(size-actual)*.5;size=actual
        self.draw_image_path(path,position+size*.5,Vector2(size.x/source.get_width(),size.y/source.get_height()),
                             rotation=rotation,world=False,tint=tint,pixel_perfect=pixel_perfect)

    def draw_ui_text(self,text,position,size,font_size,color,font_path='',align='left',vertical='top',wrap=True,font_stretch=1.0,auto_fit=True,bold=False):
        if size.x < 2 or size.y < 5: return
        name=self.resolve_asset(font_path) if font_path else ''
        stretch=max(.05,min(20,float(font_stretch)))
        fontsize=max(9,min(512,round(font_size)))
        def layout(fs):
            key=(name,fs,bool(bold))
            if key not in self._font_cache:
                self._font_cache[key]=self.pygame.font.Font(name or None,fs)
                self._font_cache[key].set_bold(bool(bold))
                if len(self._font_cache)>128:self._font_cache.pop(next(iter(self._font_cache)))
            font=self._font_cache[key]; lines=[]
            for paragraph in str(text).split('\n'):
                line=''
                for word in paragraph.split(' '):
                    candidate=(line+' '+word).strip()
                    if wrap and line and font.size(candidate)[0]*stretch>size.x:
                        lines.append(line);line=word
                    else:line=candidate
                lines.append(line)
            return font,lines
        font,lines=layout(fontsize)
        while auto_fit and fontsize>9 and (font.get_linesize()*len(lines)>size.y or any(font.size(t)[0]*stretch>size.x for t in lines)):
            fontsize-=1;font,lines=layout(fontsize)
        height=font.get_linesize()*len(lines)
        y=position.y+(size.y-height)*(.5 if vertical=='center' else 1 if vertical=='bottom' else 0)
        old_clip=self.screen.get_clip()
        self.screen.set_clip(self.pygame.Rect(round(position.x),round(position.y),round(size.x),round(size.y)).clip(old_clip))
        for line in lines:
            key=(name,fontsize,line,tuple(color),round(stretch,5),bool(bold))
            surface=self._text_cache.get(key)
            if surface is None:
                surface=font.render(line,True,color[:3])
                if abs(stretch-1)>1e-5 and surface.get_width()>0:
                    surface=self.pygame.transform.smoothscale(surface,(max(1,round(surface.get_width()*stretch)),surface.get_height()))
                if len(color)>3 and color[3]<255:surface.set_alpha(color[3])
                cost=surface.get_width()*surface.get_height()*4
                if cost<4*1024*1024:
                    self._text_cache[key]=surface;self._text_cache_bytes+=cost
                    while self._text_cache_bytes>16*1024*1024 or len(self._text_cache)>512:
                        _,old=self._text_cache.popitem(last=False)
                        self._text_cache_bytes-=old.get_width()*old.get_height()*4
            x=position.x+(size.x-surface.get_width())*(.5 if align=='center' else 1 if align=='right' else 0)
            self.screen.blit(surface,(round(x),round(y)));y+=font.get_linesize()
        self.screen.set_clip(old_clip)

    def configure_window(self,width=None,height=None,fullscreen=False,vsync=True):
        pg=self.pygame
        w=int(width or self.size.x); h=int(height or self.size.y)
        if self.offscreen:
            if (w, h) != self.screen.get_size():
                self.screen = pg.Surface((max(320, w), max(180, h))).convert()
            return
        flags=pg.FULLSCREEN if fullscreen else pg.RESIZABLE
        try:self.screen=pg.display.set_mode((max(320,w),max(180,h)),flags,vsync=int(vsync))
        except (TypeError,pg.error):self.screen=pg.display.set_mode((max(320,w),max(180,h)),flags)

    def draw_text(self, text: str, position: Vector2, size: int=20, color=(240, 240, 240), font_name: str='', world: bool=False) -> None:
        font_name = self.resolve_asset(font_name) if font_name else ''
        key = (font_name, size)
        font = self._font_cache.get(key)
        if font is None:
            font = self.pygame.font.Font(font_name or None, size)
            self._font_cache[key] = font
            if len(self._font_cache)>128:self._font_cache.pop(next(iter(self._font_cache)))
        surface = font.render(str(text), True, color)
        self.screen.blit(surface, self._point(position, world))


    def set_directional_light_3d(self, direction: Vector3, color=(255, 244, 220), energy: float=1.0, ambient: float=0.22) -> None:
        self._light3d_direction = direction.normalized if direction.length else Vector3(-0.4, -1.0, -0.6).normalized
        self._light3d_color = tuple(color[:3])
        self._light3d_energy = max(0.0, float(energy))
        self._ambient3d_energy = max(0.0, float(ambient))

    def set_environment_3d(self, ambient_color=(255, 255, 255), ambient_energy: float=0.22, fog_enabled: bool=False, fog_color=(100, 120, 145), fog_near: float=20.0, fog_far: float=100.0, sky_enabled: bool=False, sky_top_color=(35, 50, 82), sky_bottom_color=(145, 185, 225)) -> None:
        self._ambient3d_color = tuple(ambient_color[:3])
        self._ambient3d_energy = max(0.0, float(ambient_energy))
        self._fog3d_enabled = bool(fog_enabled)
        self._fog3d_color = tuple(fog_color[:3])
        self._fog3d_near = max(0.0, float(fog_near))
        self._fog3d_far = max(self._fog3d_near + 0.001, float(fog_far))
        self._sky3d_enabled = bool(sky_enabled)
        self._sky3d_top_color = tuple(sky_top_color[:3])
        self._sky3d_bottom_color = tuple(sky_bottom_color[:3])

    def prepare_scene_3d(self, root) -> None:
        from ..scene.three_d import Camera3DNode, DirectionalLight3D, PointLight3D, SpotLight3D, WorldEnvironment3D
        self._geometry_cache_3d().begin_frame()
        nodes = tuple(visible_nodes(root))
        self.render_stats = {'meshes':0,'culled':0,'faces':0}
        self._point_lights3d.clear()
        self._spot_lights3d.clear()
        self._light3d_direction = Vector3(-0.4, -1.0, -0.6).normalized
        self._light3d_color = (255, 244, 220)
        self._light3d_energy = 1.0
        self._ambient3d_color = (255, 255, 255)
        self._ambient3d_energy = 0.22
        self._fog3d_enabled = False
        self._fog3d_color = (100, 120, 145)
        self._fog3d_near = 20.0
        self._fog3d_far = 100.0
        self._sky3d_enabled = False
        self.camera3d.source_node = None
        self.camera3d.position = Vector3(0.0, 2.0, 6.0)
        self.camera3d.rotation = Vector3()
        self.camera3d.fov = 70.0
        self.camera3d.near = 0.05
        self.camera3d.far = 2000.0
        self.camera3d.orthographic = False
        self.camera3d.ortho_size = 10.0
        self.camera3d.cull_mask = 0xFFFFFFFF
        self.camera3d.enabled = True
        camera_node = next((n for n in nodes if isinstance(n, Camera3DNode) and n.current), None)
        if camera_node is not None:
            camera_node.sync_renderer(self)
        else:
            self.camera3d.source_node = None
        environment = next((n for n in nodes if isinstance(n, WorldEnvironment3D)), None)
        if environment is not None:
            self.set_environment_3d(
                environment.ambient_color,
                environment.ambient_energy,
                environment.fog_enabled,
                environment.fog_color,
                environment.fog_near,
                environment.fog_far,
                environment.sky_enabled,
                environment.sky_top_color,
                environment.sky_bottom_color,
            )
        directional = next((n for n in nodes if isinstance(n, DirectionalLight3D) and n.enabled), None)
        if directional is not None:
            self.set_directional_light_3d(directional.direction, directional.color, directional.energy, directional.ambient)
        for node in nodes:
            if isinstance(node, SpotLight3D) and node.enabled and node.visible:
                self._spot_lights3d.append({
                    'position': node.global_position,
                    'direction': node.direction,
                    'color': tuple(node.color[:3]),
                    'energy': max(0.0, float(node.energy)),
                    'range': max(0.001, float(node.range)),
                    'attenuation': max(0.01, float(node.attenuation)),
                    'angle': max(1.0, min(179.0, float(node.spot_angle))),
                    'softness': max(0.0, min(1.0, float(node.edge_softness))),
                })
            elif isinstance(node, PointLight3D) and node.enabled and node.visible:
                self._point_lights3d.append({
                    'position': node.global_position,
                    'color': tuple(node.color[:3]),
                    'energy': max(0.0, float(node.energy)),
                    'range': max(0.001, float(node.range)),
                    'attenuation': max(0.01, float(node.attenuation)),
                })
        if self._sky3d_enabled:
            self._draw_sky_3d()
        self._view3d = None

    def _draw_sky_3d(self) -> None:
        w, h = self.screen.get_size()
        if h <= 0:
            return
        for y in range(h):
            t = y / max(1, h - 1)
            color = self._mix_color(self._sky3d_top_color, self._sky3d_bottom_color, t)
            self.pygame.draw.line(self.screen, color, (0, y), (w, y))

    def _mesh3d(self, primitive: str, segments: int, rings: int) -> Mesh3D:
        key = (str(primitive).lower(), int(segments), int(rings))
        mesh = self._mesh3d_cache.get(key)
        if mesh is None:
            mesh = Mesh3D.from_primitive(key[0], key[1], key[2])
            self._mesh3d_cache[key] = mesh
        return mesh

    def _camera_space_3d(self, point: Vector3) -> Vector3:
        return self._projection_3d().view(point)

    def _project_view_3d(self, view: Vector3) -> tuple[float, float, float] | None:
        return self._projection_3d().project_view(view)

    def _geometry_cache_3d(self):
        if not hasattr(self,'_geometry3d'):self._geometry3d=GeometryCache3D()
        return self._geometry3d

    def _projection_3d(self):
        cam=self.camera3d
        parent_matrix=self._geometry_cache_3d().transforms.matrix(cam.source_node) if cam.source_node is not None else None
        key=(cam.position.x,cam.position.y,cam.position.z,cam.rotation.x,cam.rotation.y,cam.rotation.z,
             cam.fov,cam.near,cam.far,cam.orthographic,cam.ortho_size,self.screen.get_size(),parent_matrix)
        cached=getattr(self,'_view3d',None)
        if cached is None or cached[0]!=key:
            cached=key,Projection3D.from_camera(cam,*self.screen.get_size());self._view3d=cached
        return cached[1]

    def project_3d(self, point: Vector3) -> tuple[float, float, float] | None:
        return self._project_view_3d(self._camera_space_3d(point))

    @staticmethod
    def _mix_color(a, b, t: float):
        t = max(0.0, min(1.0, t))
        return tuple(max(0, min(255, round(a[i] * (1.0 - t) + b[i] * t))) for i in range(3))

    @staticmethod
    def _clip_depth_plane(points: list[Vector3], depth: float, keep_nearer: bool) -> list[Vector3]:
        if not points:
            return []
        boundary_z = -depth
        def inside(p: Vector3) -> bool:
            return p.z >= boundary_z if keep_nearer else p.z <= boundary_z
        output = []
        prev = points[-1]
        prev_inside = inside(prev)
        for current in points:
            current_inside = inside(current)
            if current_inside != prev_inside:
                denom = current.z - prev.z
                if abs(denom) > 1e-12:
                    t = (boundary_z - prev.z) / denom
                    output.append(prev.lerp(current, t))
            if current_inside:
                output.append(current)
            prev = current
            prev_inside = current_inside
        return output

    def _clip_camera_polygon(self, points: list[Vector3]) -> list[Vector3]:
        points = self._clip_depth_plane(points, self.camera3d.near, False)
        points = self._clip_depth_plane(points, self.camera3d.far, True)
        return points

    def _light_face_3d(self, base_color, normal: Vector3, center: Vector3, shaded: bool, receive_light: bool=True):
        if not shaded or not receive_light:
            return tuple(base_color[:3])
        factors = [(self._ambient3d_color[i] / 255.0) * self._ambient3d_energy for i in range(3)]
        directional = max(0.0, normal.dot(-self._light3d_direction)) if normal.length else 0.0
        for i in range(3):
            factors[i] += (self._light3d_color[i] / 255.0) * directional * self._light3d_energy
        for light in self._point_lights3d:
            delta = light['position'] - center
            distance = delta.length
            if distance <= 1e-9 or distance > light['range']:
                continue
            direction = delta / distance
            lambert = max(0.0, normal.dot(direction))
            falloff = max(0.0, 1.0 - distance / light['range']) ** light['attenuation']
            for i in range(3):
                factors[i] += (light['color'][i] / 255.0) * lambert * falloff * light['energy']
        import math
        for light in self._spot_lights3d:
            delta = center - light['position']
            distance = delta.length
            if distance <= 1e-9 or distance > light['range']:
                continue
            from_light = delta / distance
            cone = max(-1.0, min(1.0, light['direction'].dot(from_light)))
            angle = math.degrees(math.acos(cone))
            half = light['angle'] * 0.5
            if angle > half:
                continue
            edge_start = half * (1.0 - light['softness'])
            cone_factor = 1.0 if angle <= edge_start else max(0.0, (half - angle) / max(0.001, half - edge_start))
            lambert = max(0.0, normal.dot(-from_light))
            falloff = max(0.0, 1.0 - distance / light['range']) ** light['attenuation']
            for i in range(3):
                factors[i] += (light['color'][i] / 255.0) * lambert * falloff * cone_factor * light['energy']
        return tuple(max(0, min(255, round(base_color[i] * min(2.0, factors[i])))) for i in range(3))

    def queue_mesh_3d(self, node) -> None:
        if not (self.camera3d.cull_mask & (1 << max(0, min(31, int(getattr(node, 'render_layer', 0)))))):
            return
        cache=self._geometry_cache_3d();view=self._projection_3d()
        mesh=cache.mesh(node,self.project_root)
        entry=cache.entry(node,mesh)
        stats=getattr(self,'render_stats',None)
        if stats is not None:stats['meshes']+=1
        if not view.sphere_visible(entry.center,entry.radius):
            if stats is not None:stats['culled']+=1
            return
        entry.prepare()
        view_vertices=[view.view(v) for v in entry.vertices]
        projected_vertices=[view.project_view(v) for v in view_vertices]
        fully_inside=all(p is not None and 0<=p[0]<=view.width and 0<=p[1]<=view.height for p in projected_vertices)
        base_color = tuple(getattr(node, 'color', (110, 170, 235))[:3])
        wire = bool(getattr(node, 'wireframe', False))
        shaded = bool(getattr(node, 'shaded', True))
        double_sided = bool(getattr(node, 'double_sided', True))
        receive_light = bool(getattr(node, 'receive_light', True))
        colors=None
        if not self._point_lights3d and not self._spot_lights3d:
            d=self._light3d_direction
            light_key=(base_color,shaded,receive_light,d.x,d.y,d.z,self._light3d_color,self._light3d_energy,self._ambient3d_color,self._ambient3d_energy)
            if getattr(entry,'lighting_key',None)!=light_key:
                entry.lighting_key=light_key
                entry.lighting_colors=[self._light_face_3d(base_color,n,c,shaded,receive_light) for _,n,c in entry.faces]
            colors=entry.lighting_colors
        if getattr(self, '_gpu3d', None) is not None and not wire:


            for index,(face,normal,center) in enumerate(entry.faces):
                if not double_sided and normal.dot(self.camera3d.position-center)<=0.0:
                    continue
                color = colors[index] if colors is not None else self._light_face_3d(base_color,normal,center,shaded,receive_light)
                if self._fog3d_enabled:
                    depth = -sum(view_vertices[i].z for i in face)/len(face)
                    color = self._mix_color(color,self._fog3d_color,
                        (depth-self._fog3d_near)/max(.001,self._fog3d_far-self._fog3d_near))
                self._gpu3d.add_face([view_vertices[i] for i in face],color)
                if stats is not None:stats['faces']+=1
            return
        for index,(face,normal,center) in enumerate(entry.faces):
            if not double_sided:
                to_camera = self.camera3d.position - center
                if normal.dot(to_camera) <= 0.0:
                    continue
            if fully_inside:
                pp=[projected_vertices[i] for i in face]
                depth=sum(p[2] for p in pp)/len(pp)
            else:
                depth_vertices=self._clip_camera_polygon([view_vertices[i] for i in face])
                if len(depth_vertices)<3:continue


                depth=-sum(v.z for v in depth_vertices)/len(depth_vertices)
                clipped = view.clip(depth_vertices)
                if len(clipped) < 3:continue
                pp = [view.project_view(v) for v in clipped]
                if any(p is None for p in pp):continue
            screen_points = [(round(p[0]), round(p[1])) for p in pp]
            color = colors[index] if colors is not None else self._light_face_3d(base_color, normal, center, shaded, receive_light)
            if self._fog3d_enabled:
                fog_t = (depth - self._fog3d_near) / max(0.001, self._fog3d_far - self._fog3d_near)
                color = self._mix_color(color, self._fog3d_color, fog_t)
            self._triangles3d.append((depth, screen_points, color, wire))
            if stats is not None:stats['faces']+=1

    def queue_box_3d(self, node, offset: Vector3, size: Vector3, color=(80, 230, 120)) -> None:
        if not hasattr(self,'_debug_cube'):self._debug_cube=Mesh3D.cube()
        cache=self._geometry_cache_3d();view=self._projection_3d()
        entry=cache.entry(node,self._debug_cube,size,offset)
        if not view.sphere_visible(entry.center,entry.radius):return
        entry.prepare();vertices=[view.view(v) for v in entry.vertices]
        for face,_,_ in entry.faces:
            depth_vertices=self._clip_camera_polygon([vertices[i] for i in face])
            if len(depth_vertices)<3:continue
            depth=-sum(v.z for v in depth_vertices)/len(depth_vertices)
            clipped=view.clip(depth_vertices)
            if len(clipped)<3:continue
            pp=[view.project_view(v) for v in clipped]
            if any(p is None for p in pp):continue
            self._triangles3d.append((depth,[(round(p[0]),round(p[1])) for p in pp],tuple(color[:3]),True))

    def flush_3d(self) -> None:
        if getattr(self, '_gpu3d', None) is not None and self._gpu3d.vertices:
            try:
                surface = self._gpu3d.draw(self._projection_3d(), self.pygame)
                if surface is not None: self.screen.blit(surface, (0, 0))
            except Exception as exc:
                logging.getLogger('VWorks.renderer').exception('GPU 3D render failed; switching to CPU: %s',exc)
                try:self._gpu3d.release()
                except Exception:pass
                self._gpu3d = None
                self.active_3d_backend = 'cpu (GPU failed)'
        if not self._triangles3d:
            return
        self._triangles3d.sort(key=lambda item: item[0], reverse=True)
        for _, points, color, wire in self._triangles3d:
            if len(points) < 3:
                continue
            if wire:
                self.pygame.draw.polygon(self.screen, color, points, 1)
            else:
                self.pygame.draw.polygon(self.screen, color, points, 0)
                self.pygame.draw.polygon(self.screen, tuple(max(0, c - 35) for c in color), points, 1)
        self._triangles3d.clear()

    def shutdown(self) -> None:
        if getattr(self, '_gpu3d', None) is not None:
            try:self._gpu3d.release()
            except Exception:pass
            self._gpu3d = None
        self._sprite_cache.clear();self._text_cache.clear()
        self._image_cache.clear()
        self._resource_cache.clear()
        self._font_cache.clear()
        self._mesh3d_cache.clear()
        self._triangles3d.clear()
        self.pygame.display.quit()
        self.pygame.quit()



from .window_lifecycle import install_window_lifecycle
install_window_lifecycle(PygameRenderer)
