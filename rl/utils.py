from __future__ import annotations

import csv
import hashlib
import os
import re
import time
from datetime import datetime
from typing import Dict, Iterable, List, Optional


_slugify_re = re.compile(r"[^a-z0-9\-]+")
_whitespace_re = re.compile(r"\s+")


def sha1_hex(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def slugify(text: str, max_len: int = 80) -> str:
    text = text.strip().lower()
    text = _whitespace_re.sub("-", text)
    text = _slugify_re.sub("-", text)
    text = text.strip("-")
    if len(text) > max_len:
        text = text[:max_len].rstrip("-")
    return text or "untitled"


def safe_filename(path: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._\-/]", "_", path)


def ensure_parent_dir(path: str) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)


def parse_date(s: str) -> Optional[datetime]:
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y/%m/%d %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            continue
    return None


def iso_date(d: datetime) -> str:
    return d.strftime("%Y-%m-%d")


def sleep_polite(seconds: float) -> None:
    if seconds > 0:
        time.sleep(seconds)


def write_csv(path: str, rows: Iterable[Dict[str, object]], fieldnames: List[str]) -> None:
    ensure_parent_dir(path)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for row in rows:
            w.writerow(row)
