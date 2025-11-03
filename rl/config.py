from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class Settings:
    base_url: str = "https://www.newyorker.com"
    data_dir: str = os.path.abspath(os.path.join(os.getcwd(), "data"))
    cache_dir: str = os.path.abspath(os.path.join(os.getcwd(), "data", "cache", "http"))
    raw_dir: str = os.path.abspath(os.path.join(os.getcwd(), "data", "raw"))
    extracted_dir: str = os.path.abspath(os.path.join(os.getcwd(), "data", "extracted"))
    metrics_dir: str = os.path.abspath(os.path.join(os.getcwd(), "data", "metrics"))
    logs_dir: str = os.path.abspath(os.path.join(os.getcwd(), "data", "logs"))

    # politeness
    request_timeout_s: float = 30.0
    request_delay_s: float = 1.0
    max_retries: int = 3

    # web alignment window (± days)
    week_radius_days: int = 3

    # clipping for outliers (disabled by default)
    clip_metric_min: Optional[float] = None
    clip_metric_max: Optional[float] = None

    user_agent: str = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0 Safari/537.36"
    )


def ensure_dirs(cfg: Settings) -> None:
    for d in [
        cfg.data_dir,
        cfg.cache_dir,
        cfg.raw_dir,
        cfg.extracted_dir,
        cfg.metrics_dir,
        cfg.logs_dir,
        os.path.join(cfg.raw_dir, "magazine"),
        os.path.join(cfg.raw_dir, "web"),
        os.path.join(cfg.extracted_dir, "magazine"),
        os.path.join(cfg.extracted_dir, "web"),
    ]:
        os.makedirs(d, exist_ok=True)


def find_default_cookies() -> Optional[str]:
    cwd = os.getcwd()
    candidates = [
        os.path.join(cwd, "data", "ny.json"),
        os.path.join(cwd, "rl", "ny.json"),
        os.path.join(cwd, "cookies.json"),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None


def load_cookies(cookies_path: Optional[str]) -> List[Dict[str, str]]:
    if not cookies_path:
        return []
    if not os.path.exists(cookies_path):
        raise FileNotFoundError(f"cookies file not found: {cookies_path}")
    with open(cookies_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    # Support both cookie-jar list and Netscape-like export via extensions
    cookies: List[Dict[str, str]] = []
    if isinstance(data, list):
        for c in data:
            if "name" in c and "value" in c:
                cookies.append({
                    "name": c["name"],
                    "value": c["value"],
                    "domain": c.get("domain", ".newyorker.com"),
                    "path": c.get("path", "/"),
                })
    elif isinstance(data, dict) and "cookies" in data:
        for c in data["cookies"]:
            cookies.append({
                "name": c["name"],
                "value": c["value"],
                "domain": c.get("domain", ".newyorker.com"),
                "path": c.get("path", "/"),
            })
    return cookies
