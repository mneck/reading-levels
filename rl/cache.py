from __future__ import annotations

import os
from typing import Optional

from .utils import ensure_parent_dir, sha1_hex


class SimpleCache:
    def __init__(self, cache_dir: str) -> None:
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)

    def _path_for(self, key: str) -> str:
        digest = sha1_hex(key)
        subdir = os.path.join(self.cache_dir, digest[:2])
        os.makedirs(subdir, exist_ok=True)
        return os.path.join(subdir, f"{digest}.bin")

    def get(self, key: str) -> Optional[bytes]:
        path = self._path_for(key)
        if os.path.exists(path):
            try:
                with open(path, "rb") as f:
                    return f.read()
            except Exception:
                return None
        return None

    def set(self, key: str, value: bytes) -> None:
        path = self._path_for(key)
        ensure_parent_dir(path)
        with open(path, "wb") as f:
            f.write(value)
