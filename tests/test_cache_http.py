import os
from types import SimpleNamespace

from rl.cache import SimpleCache
from rl.config import Settings
from rl.http import HttpClient


def test_simple_cache_roundtrip(tmp_path):
    cache_dir = tmp_path / "cache"
    cache = SimpleCache(str(cache_dir))
    key = "https://example.com/path?q=1"
    val = b"hello world"
    assert cache.get(key) is None
    cache.set(key, val)
    got = cache.get(key)
    assert got == val
    # ensure sharded directory exists
    subdirs = list((tmp_path / "cache").iterdir())
    assert len(subdirs) == 1


def test_httpclient_loads_cookies(tmp_path):
    cfg = Settings(
        data_dir=str(tmp_path / "data"),
        cache_dir=str(tmp_path / "data" / "cache" / "http"),
        raw_dir=str(tmp_path / "data" / "raw"),
        extracted_dir=str(tmp_path / "data" / "extracted"),
        metrics_dir=str(tmp_path / "data" / "metrics"),
        logs_dir=str(tmp_path / "data" / "logs"),
    )
    cookies = [
        {"name": "CN_token_access", "value": "abc", "domain": ".newyorker.com", "path": "/"}
    ]
    http = HttpClient(cfg, cookies=cookies)
    cookie_names = {c.name for c in http.session.cookies}
    assert "CN_token_access" in cookie_names
