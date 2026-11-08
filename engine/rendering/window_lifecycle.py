




from functools import wraps
from inspect import signature
import logging


def install_window_lifecycle(renderer_class):
    if renderer_class.__dict__.get('_window_lifecycle_v3', False):
        return renderer_class
    original_init = renderer_class.__init__
    original_configure = renderer_class.configure_window
    original_clear = renderer_class.clear
    original_present = renderer_class.present
    original_size = renderer_class.size
    init_signature = signature(original_init)
    log = logging.getLogger('VWorks.window')

    def invalidate(self):
        self.screen.set_clip(None)
        for key in ('_sprite_cache', '_text_cache'):
            cache = getattr(self, key, None)
            if cache is not None:
                cache.clear()
        for key in ('_sprite_cache_bytes', '_text_cache_bytes'):
            if hasattr(self, key):
                setattr(self, key, 0)

    def refresh(self):

        if getattr(self, '_window_fix_offscreen', False) or not hasattr(self, '_window_surface_size'):
            return
        surface = self.pygame.display.get_surface()
        if surface is None:
            raise RuntimeError('The SDL display surface was lost; restart the game.')
        dimensions = surface.get_size()

        if surface is not self.screen or dimensions != self._window_surface_size:
            self.screen = surface
            self._window_surface_size = dimensions
            if not self._window_mode[0]:
                self._window_restore_size = dimensions
            invalidate(self)

    def flags_for(self, fullscreen):
        pg = self.pygame
        flags = pg.FULLSCREEN if fullscreen else (pg.RESIZABLE if self._window_resizable else 0)
        if self._window_borderless:
            flags |= pg.NOFRAME
        return flags

    def set_mode(self, dimensions, flags, vsync):
        try:
            return self.pygame.display.set_mode(dimensions, flags, vsync=int(vsync))
        except (TypeError, self.pygame.error):
            return self.pygame.display.set_mode(dimensions, flags)

    @wraps(original_init)
    def initialize(self, *args, **kwargs):
        bound = init_signature.bind(self, *args, **kwargs)
        bound.apply_defaults()
        original_init(self, *args, **kwargs)
        settings = bound.arguments['window_settings']
        self._window_fix_offscreen = bool(bound.arguments.get('offscreen', False))
        self._window_surface_size = self.screen.get_size()
        self._window_mode = (bool(settings.fullscreen), bool(settings.vsync))
        self._window_resizable = bool(settings.resizable)
        self._window_borderless = bool(settings.borderless)
        self._window_restore_size = self._window_surface_size

    @wraps(original_size.fget)
    def get_size(self):
        refresh(self)
        return original_size.fget(self)

    @wraps(original_configure)
    def configure(self, width=None, height=None, fullscreen=False, vsync=True):
        if self._window_fix_offscreen:
            return original_configure(self, width, height, fullscreen, vsync)
        refresh(self)
        old_size = self.screen.get_size()
        old_mode = self._window_mode
        mode = (bool(fullscreen), bool(vsync))
        base = self._window_restore_size if old_mode[0] and not mode[0] else old_size
        requested = (max(320, int(width or base[0])), max(180, int(height or base[1])))
        if requested == old_size and mode == old_mode:
            return
        try:
            surface = set_mode(self, requested, flags_for(self, mode[0]), mode[1])
        except self.pygame.error:
            log.exception('Cannot apply display mode %s, fullscreen=%s; restoring previous mode', requested, mode[0])


            try:
                self.screen = set_mode(self, old_size, flags_for(self, old_mode[0]), old_mode[1])
            except self.pygame.error as exc:
                raise RuntimeError('Cannot restore the previous SDL display mode.') from exc
            self._window_surface_size = self.screen.get_size()
            invalidate(self)
            return
        if not old_mode[0]:
            self._window_restore_size = old_size
        self.screen = surface
        self._window_surface_size = surface.get_size()
        self._window_mode = mode
        if not mode[0]:
            self._window_restore_size = self._window_surface_size
        invalidate(self)

    @wraps(original_clear)
    def clear(self, *args, **kwargs):
        refresh(self)
        if not getattr(self, '_window_fix_offscreen', False):

            self.screen.set_clip(None)
        return original_clear(self, *args, **kwargs)

    @wraps(original_present)
    def present(self, *args, **kwargs):
        if getattr(self, '_window_fix_offscreen', False):
            return original_present(self, *args, **kwargs)
        refresh(self)
        if self.pygame.display.get_active():
            return original_present(self, *args, **kwargs)

    renderer_class.__init__ = initialize
    renderer_class.size = property(get_size, original_size.fset, original_size.fdel, original_size.__doc__)
    renderer_class.configure_window = configure
    renderer_class.clear = clear
    renderer_class.present = present
    renderer_class._window_lifecycle_v3 = True
    return renderer_class
