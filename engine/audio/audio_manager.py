from __future__ import annotations
from pathlib import Path
from typing import Dict

class AudioManager:

    def __init__(self, pygame_module, settings) -> None:
        self.pg = pygame_module
        self.settings = settings
        self.enabled = bool(settings.enabled)
        self.sounds: Dict[str, object] = {}
        self._channel_volumes = {}
        self._pitch_cache = {}
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

    def play(self, path: str, loops: int=0, volume: float=1.0, pitch: float=1.0):
        sound = self.load(path)
        if sound is None:
            return None
        if abs(pitch-1.0) > 0.005:
            sound = self._pitched(sound, path, pitch)
        channel = sound.play(loops=loops)
        if channel is not None:
            channel.set_volume(max(0.0, min(1.0, volume * self.settings.master_volume)))
            self._channel_volumes[channel] = volume
        return channel

    def _pitched(self, sound, path, pitch):
        from array import array
        step = max(0.5, min(1.5, round(pitch*64)/64))
        key = (str(Path(path).resolve()), step)
        if key in self._pitch_cache:
            return self._pitch_cache[key]
        init = self.pg.mixer.get_init()
        if not init or init[1] != -16:
            return sound
        channels = init[2]
        samples = array('h', sound.get_raw())
        frames = len(samples)//channels
        result = array('h')
        for frame in range(int(frames/step)):
            origin = min(frames-1, int(frame*step))*channels
            result.extend(samples[origin:origin+channels])
        variant = self.pg.mixer.Sound(buffer=result.tobytes())
        if len(self._pitch_cache) >= 48:
            self._pitch_cache.pop(next(iter(self._pitch_cache)))
        self._pitch_cache[key] = variant
        return variant

    def set_master_volume(self, value):
        self.settings.master_volume = max(0.0,min(1.0,float(value)))
        for channel, volume in list(self._channel_volumes.items()):
            if channel.get_busy(): channel.set_volume(volume*self.settings.master_volume)
            else: self._channel_volumes.pop(channel,None)

    def stop_all(self) -> None:
        if self.enabled:
            self.pg.mixer.stop()

    def clear(self) -> None:
        self.stop_all()
        self.sounds.clear()
        self._pitch_cache.clear()
        self._channel_volumes.clear()
