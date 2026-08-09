import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


class JsonCache:
    def __init__(self, root: Path, ttl_hours: int = 18):
        self.root = Path(root)
        self.ttl = timedelta(hours=ttl_hours)

    def _path(self, key: str) -> Path:
        safe_key = "".join(character for character in key if character.isalnum() or character in "-_")
        return self.root / f"{safe_key}.json"

    def get(self, key: str) -> dict[str, Any] | None:
        path = self._path(key)
        if not path.exists():
            return None
        modified = datetime.fromtimestamp(path.stat().st_mtime)
        if datetime.now() - modified > self.ttl:
            return None
        try:
            with path.open("r", encoding="utf-8") as file:
                return json.load(file)
        except (OSError, json.JSONDecodeError):
            return None

    def set(self, key: str, value: dict[str, Any]) -> Path:
        self.root.mkdir(parents=True, exist_ok=True)
        path = self._path(key)
        temporary = path.with_suffix(".tmp")
        with temporary.open("w", encoding="utf-8") as file:
            json.dump(value, file, ensure_ascii=False, indent=2)
        temporary.replace(path)
        return path

