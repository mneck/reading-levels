from __future__ import annotations

import time
from typing import Dict, List, Optional

import requests
from requests import Response

from .cache import SimpleCache
from .config import Settings
from .utils import sleep_polite


class HttpClient:
    def __init__(self, cfg: Settings, cookies: Optional[List[Dict[str, str]]] = None) -> None:
        self.cfg = cfg
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": cfg.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        })
        self.cache = SimpleCache(cfg.cache_dir)
        if cookies:
            for c in cookies:
                # requests cookie requires domain without leading dot sometimes
                domain = c.get("domain", ".newyorker.com").lstrip(".")
                self.session.cookies.set(c["name"], c["value"], domain=domain, path=c.get("path", "/"))

    def get(self, url: str, use_cache: bool = True) -> Response:
        if use_cache:
            cached = self.cache.get(url)
            if cached is not None:
                # Build a fake Response
                r = requests.Response()
                r.status_code = 200
                r._content = cached
                r.url = url
                r.headers["X-Cache-Hit"] = "1"
                return r

        last_exc: Optional[Exception] = None
        for attempt in range(self.cfg.max_retries):
            try:
                sleep_polite(self.cfg.request_delay_s)
                r = self.session.get(url, timeout=self.cfg.request_timeout_s)
                if r.status_code == 200:
                    if use_cache:
                        self.cache.set(url, r.content)
                    return r
                # For soft-blocks, backoff
                if r.status_code in (403, 429, 503):
                    time.sleep(2.0 * (attempt + 1))
                    continue
                r.raise_for_status()
                return r
            except Exception as e:
                last_exc = e
                time.sleep(1.0 * (attempt + 1))
        if last_exc:
            raise last_exc
        raise RuntimeError("HTTP get failed for unknown reasons")

    def get_rendered(self, url: str, playwright_timeout_ms: int = 20000) -> str:
        # Lazy import to avoid heavy startup cost
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(user_agent=self.cfg.user_agent)
            # transfer cookies into context
            for c in self.session.cookies:
                try:
                    context.add_cookies([
                        {
                            "name": c.name,
                            "value": c.value,
                            "domain": c.domain if c.domain else "www.newyorker.com",
                            "path": c.path or "/",
                        }
                    ])
                except Exception:
                    pass
            page = context.new_page()
            page.goto(url, timeout=playwright_timeout_ms)
            page.wait_for_load_state("networkidle")
            html = page.content()
            browser.close()
            # cache rendered content too
            self.cache.set(url + "#rendered", html.encode("utf-8"))
            return html
