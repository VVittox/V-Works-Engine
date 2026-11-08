from __future__ import annotations
from datetime import datetime
from enum import IntEnum
import sys

class LogLevel(IntEnum):
    DEBUG = 0
    INFO = 1
    WARN = 2
    ERROR = 3
    CRITICAL = 4

class VLogger:
    COLORS = {LogLevel.DEBUG: '\x1b[90m', LogLevel.INFO: '\x1b[36m', LogLevel.WARN: '\x1b[33m', LogLevel.ERROR: '\x1b[31m', LogLevel.CRITICAL: '\x1b[41m'}
    RESET = '\x1b[0m'
    TAGS = {LogLevel.DEBUG: 'DEBUG', LogLevel.INFO: 'INFO ', LogLevel.WARN: 'WARN ', LogLevel.ERROR: 'ERROR', LogLevel.CRITICAL: 'FATAL'}

    def __init__(self, min_level: LogLevel=LogLevel.DEBUG, tag: str='VWorks') -> None:
        self.min_level = min_level
        self.tag = tag

    def _log(self, level: LogLevel, msg: str) -> None:
        if level < self.min_level:
            return
        color = self.COLORS.get(level, '')
        tag = self.TAGS.get(level, '?????')
        ts = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        stream = sys.stderr if level >= LogLevel.ERROR else sys.stdout
        print(f'{color}[{ts}] [{tag}] [{self.tag}] {msg}{self.RESET}', file=stream)

    def debug(self, msg: str) -> None:
        self._log(LogLevel.DEBUG, msg)

    def info(self, msg: str) -> None:
        self._log(LogLevel.INFO, msg)

    def warn(self, msg: str) -> None:
        self._log(LogLevel.WARN, msg)

    def error(self, msg: str) -> None:
        self._log(LogLevel.ERROR, msg)

    def critical(self, msg: str) -> None:
        self._log(LogLevel.CRITICAL, msg)
