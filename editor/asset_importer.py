from __future__ import annotations
import hashlib
import json
import mimetypes
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

@dataclass
class ImportedAsset:
    source: Path
    destination: Path
    kind: str
    metadata_path: Path

class AssetImporter:

    def __init__(self, project_dir: str | Path) -> None:
        self.project_dir = Path(project_dir).resolve()
        self.assets_dir = self.project_dir / 'assets'
        self.meta_dir = self.project_dir / '.vworks' / 'imports'
        self.meta_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def classify(path: Path) -> str:
        ext = path.suffix.lower()
        if ext in {'.png', '.jpg', '.jpeg', '.bmp', '.webp', '.gif'}:
            return 'texture'
        if ext in {'.wav', '.ogg', '.mp3', '.flac'}:
            return 'audio'
        if ext in {'.ttf', '.otf'}:
            return 'font'
        if ext in {'.obj', '.stl'}:
            return 'mesh3d'
        if ext in {'.vmat'}:
            return 'material'
        if ext in {'.vshader'}:
            return 'shader'
        if ext in {'.vprefab'}:
            return 'prefab'
        if ext in {'.vscene'}:
            return 'scene'
        if ext in {'.py'}:
            return 'script'
        return 'file'

    def _metadata_path(self, destination: Path) -> Path:
        rel = destination.resolve().relative_to(self.project_dir).as_posix()
        digest = hashlib.sha1(rel.encode('utf-8')).hexdigest()[:16]
        return self.meta_dir / f'{digest}.vimport'

    def import_file(self, source: str | Path, subfolder: str='') -> ImportedAsset:
        src = Path(source).expanduser().resolve()
        if not src.is_file():
            raise FileNotFoundError(src)
        target_dir = (self.assets_dir / subfolder).resolve()
        try:
            target_dir.relative_to(self.assets_dir.resolve())
        except ValueError as exc:
            raise ValueError('Import destination must be inside assets/') from exc
        target_dir.mkdir(parents=True, exist_ok=True)
        dst = target_dir / src.name
        if src != dst.resolve():
            if dst.exists():
                stem, ext = (dst.stem, dst.suffix)
                i = 2
                while dst.exists():
                    dst = target_dir / f'{stem}_{i}{ext}'
                    i += 1
            shutil.copy2(src, dst)
        kind = self.classify(dst)
        stat = dst.stat()
        mime, _ = mimetypes.guess_type(dst.name)
        payload = {'format': 'vworks_import', 'version': 1, 'kind': kind, 'source': str(src), 'asset': dst.resolve().relative_to(self.project_dir).as_posix(), 'size': stat.st_size, 'mtime': stat.st_mtime, 'mime': mime or 'application/octet-stream', 'settings': {'filter': 'linear', 'wrap': 'clamp'} if kind == 'texture' else {}}
        meta = self._metadata_path(dst)
        meta.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
        self.rebuild_index()
        return ImportedAsset(src, dst, kind, meta)

    def scan_assets(self) -> list[dict]:
        result = []
        if not self.assets_dir.exists():
            return result
        for path in sorted((p for p in self.assets_dir.rglob('*') if p.is_file())):
            rel = path.relative_to(self.project_dir).as_posix()
            result.append({'path': rel, 'kind': self.classify(path), 'size': path.stat().st_size})
        return result

    def rebuild_index(self) -> Path:
        index = self.project_dir / '.vworks' / 'asset_index.json'
        index.parent.mkdir(parents=True, exist_ok=True)
        index.write_text(json.dumps({'format': 'vworks_asset_index', 'version': 1, 'assets': self.scan_assets()}, ensure_ascii=False, indent=2), encoding='utf-8')
        return index

    def import_many(self, paths: Iterable[str | Path], subfolder: str='') -> list[ImportedAsset]:
        return [self.import_file(p, subfolder) for p in paths]
