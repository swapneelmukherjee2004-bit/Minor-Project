"""Screenshot storage abstraction. Local implementation confines all paths to a root directory."""
import uuid
from pathlib import Path
from typing import Protocol


class Storage(Protocol):
    def save_screenshot(self, audit_id: str, data: bytes) -> str: ...
    def read(self, key: str) -> bytes | None: ...
    def delete(self, key: str) -> None: ...


class LocalStorage:
    def __init__(self, root: Path):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _safe(self, key: str) -> Path:
        p = (self.root / key).resolve()
        if self.root not in p.parents:
            raise ValueError("invalid storage key")
        return p

    def save_screenshot(self, audit_id: str, data: bytes) -> str:
        uuid.UUID(audit_id)  # generated names only; rejects path tricks
        key = f"{audit_id}.png"
        self._safe(key).write_bytes(data)
        return key

    def read(self, key: str) -> bytes | None:
        p = self._safe(key)
        return p.read_bytes() if p.exists() else None

    def delete(self, key: str) -> None:
        p = self._safe(key)
        if p.exists():
            p.unlink()
