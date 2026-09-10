from __future__ import annotations
from pathlib import Path
from typing import Dict

class AudioManager:

    def __init__(self, pygame_module, settings) -> None:
        self.pg = pygame_module
        self.settings = settings
        self.enabled = bool(settings.enabled)
        self.sounds: Dict[str, object] = {}
        if not self.enabled:
            return
        try:
            if not self.pg.mixer.get_init():
                self.pg.mixer.init(frequency=settings.frequency, buffer=settings.buffer)
            self.pg.mixer.set_num_channels(settings.channels)
        except self.pg.error:
            self.enabled = False

    def load(self, path: str):
        key = str(Path(path).resolve())
        if key not in self.sounds:
            if not self.enabled:
                return None
            self.sounds[key] = self.pg.mixer.Sound(key)
        return self.sounds[key]

    def play(self, path: str, loops: int=0, volume: float=1.0):
        sound = self.load(path)
        if sound is None:
            return None
        sound.set_volume(max(0.0, min(1.0, volume * self.settings.master_volume)))
        return sound.play(loops=loops)

    def stop_all(self) -> None:
        if self.enabled:
            self.pg.mixer.stop()

    def clear(self) -> None:
        self.stop_all()
        self.sounds.clear()
