from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, Optional, Tuple

class RenderMode(Enum):
    FORWARD = auto()
    DEFERRED = auto()
    IMMEDIATE = auto()

class PhysicsSolver(Enum):
    IMPULSE = auto()
    CONSTRAINT = auto()

class AudioDriver(Enum):
    SDL = 'SDL2_mixer'
    PORTMIDI = 'portmidi'
    NULL = 'null'

@dataclass
class WindowSettings:
    width: int = 1280
    height: int = 720
    title: str = 'V Works Engine'
    fullscreen: bool = False
    borderless: bool = False
    resizable: bool = True
    vsync: bool = True
    window_icon: Optional[str] = None
    always_on_top: bool = False

@dataclass
class RenderingSettings:
    mode: RenderMode = RenderMode.FORWARD
    anti_aliasing: int = 1
    shadow_enabled: bool = False
    shadow_resolution: int = 2048
    ambient_occlusion: bool = False
    bloom: bool = False
    bloom_strength: float = 0.5
    fog_enabled: bool = False
    fog_density: float = 0.02
    fog_color: tuple = (0.1, 0.1, 0.15)
    max_framebuffer_w: int = 4096
    max_framebuffer_h: int = 4096
    pixel_perfect: bool = False
    low_power_mode: bool = False

@dataclass
class PhysicsSettings:
    solver: PhysicsSolver = PhysicsSolver.IMPULSE
    gravity: float = 980.0
    gravity_3d: float = -9.81
    iterations: int = 8
    max_velocity: float = 4000.0
    time_scale: float = 1.0
    substeps: int = 1
    sleeping_threshold: float = 0.05
    broadphase_cell_size_2d: float = 64.0
    broadphase_cell_size_3d: float = 4.0

@dataclass
class AudioSettings:
    enabled: bool = True
    driver: AudioDriver = AudioDriver.SDL
    master_volume: float = 1.0
    channels: int = 32
    frequency: int = 44100
    buffer: int = 512

@dataclass
class EngineSettings:
    window: WindowSettings = field(default_factory=WindowSettings)
    rendering: RenderingSettings = field(default_factory=RenderingSettings)
    physics: PhysicsSettings = field(default_factory=PhysicsSettings)
    audio: AudioSettings = field(default_factory=AudioSettings)
    target_fps: int = 120
    physics_fps: int = 60
    max_frame_delta: float = 0.25
    background_color: Tuple[int, int, int] = (22, 24, 31)
    debug: bool = True
    custom: Dict[str, Any] = field(default_factory=dict)

    @property
    def physics_delta(self) -> float:
        return 1.0 / max(1, self.physics_fps)
