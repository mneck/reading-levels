from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Iterable, List, Optional, Set, Tuple

from bs4 import BeautifulSoup

from .config import Settings
from .http import HttpClient
from .parsing import extract_article_text, extract_meta
from .utils import ensure_parent_dir, iso_date, safe_filename, slugify


_ISSUE_LINK_RE = re.compile(r"^/magazine/(\d{4})/(\d{2})/(\d{2})(?:/)?$")
_MAG_ARTICLE_RE = re.compile(r"^/magazine/\d{4}/\d{2}/\d{2}/[\w\-]+/?$")


@dataclass
class Issue:
    date: datetime
    url: str


@dataclass
class Article:
    url: str
    title: Optional[str]
    author: Optional[str]
    section: Optional[str]
    published: Optional[datetime]
    issue_date: Optional[datetime]
    source: str  # "magazine" or "web"
    text: str


def _abs(base: str, href: str) -> str:
    if href.startswith("http"):
        return href
    return base.rstrip("/") + "/" + href.lstrip("/")


def get_issues_for_year(http: HttpClient, cfg: Settings, year: int) -> List[Issue]:
    url = f"{cfg.base_url}/magazine/{year}"
    r = http.get(url)
    soup = BeautifulSoup(r.text, "lxml")
    issues: Dict[str, Issue] = {}
    for a in soup.select('a[href^="/magazine/"]'):
        href = a.get("href", "")
        m = _ISSUE_LINK_RE.match(href)
        if not m:
            continue
        y, mth, d = m.groups()
        try:
            dt = datetime(int(y), int(mth), int(d))
        except Exception:
            continue
        abs_url = _abs(cfg.base_url, href)
        issues[abs_url] = Issue(date=dt, url=abs_url)
    # sort by date
    return sorted(issues.values(), key=lambda i: i.date)


def get_issue_articles(http: HttpClient, cfg: Settings, issue_url: str) -> List[str]:
    r = http.get(issue_url)
    soup = BeautifulSoup(r.text, "lxml")
    urls: Set[str] = set()
    for a in soup.select('a[href^="/magazine/"]'):
        href = a.get("href", "")
        if _MAG_ARTICLE_RE.match(href):
            urls.add(_abs(cfg.base_url, href))
    return sorted(urls)


def _save_raw_and_extracted(article: Article, cfg: Settings) -> Tuple[str, str]:
    year = article.published.year if article.published else (article.issue_date.year if article.issue_date else 1970)
    base_dir_raw = os.path.join(cfg.raw_dir, article.source, f"year={year}")
    base_dir_ex = os.path.join(cfg.extracted_dir, article.source, f"year={year}")
    ensure_parent_dir(base_dir_raw)
    ensure_parent_dir(base_dir_ex)

    slug = slugify(article.title or article.url)
    raw_path = os.path.join(base_dir_raw, safe_filename(f"{slug}.html"))
    ex_path = os.path.join(base_dir_ex, safe_filename(f"{slug}.json"))

    # raw html is expected to be saved by caller; here we ensure JSON
    meta = {
        "url": article.url,
        "title": article.title,
        "author": article.author,
        "section": article.section,
        "published": iso_date(article.published) if article.published else None,
        "issue_date": iso_date(article.issue_date) if article.issue_date else None,
        "source": article.source,
        "num_chars": len(article.text),
        "text": article.text,
    }
    ensure_parent_dir(ex_path)
    with open(ex_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False)

    return raw_path, ex_path


def fetch_magazine_issue(http: HttpClient, cfg: Settings, issue: Issue) -> List[Article]:
    article_urls = get_issue_articles(http, cfg, issue.url)
    results: List[Article] = []
    for url in article_urls:
        rr = http.get(url)
        html = rr.text
        text, meta = extract_article_text(html)
        if not text or len(text.split()) < 50:
            # fallback to rendered if needed
            try:
                html = http.get_rendered(url)
                text, meta = extract_article_text(html)
            except Exception:
                pass
        # Save raw html
        year = issue.date.year
        slug = slugify(meta.get("title") or url)
        raw_path = os.path.join(cfg.raw_dir, "magazine", f"year={year}", safe_filename(f"{slug}.html"))
        ensure_parent_dir(raw_path)
        try:
            with open(raw_path, "w", encoding="utf-8") as f:
                f.write(html)
        except Exception:
            pass

        art = Article(
            url=url,
            title=meta.get("title"),
            author=meta.get("author"),
            section=meta.get("section"),
            published=None,  # many magazine pages omit published meta; use issue date instead
            issue_date=issue.date,
            source="magazine",
            text=text or "",
        )
        _save_raw_and_extracted(art, cfg)
        results.append(art)
    return results


def _iter_sitemap_urls(http: HttpClient, cfg: Settings) -> Iterable[Tuple[str, Optional[datetime]]]:
    # Read sitemap index
    idx_url = f"{cfg.base_url}/sitemaps/newyorker/sitemap-index.xml"
    r = http.get(idx_url)
    soup = BeautifulSoup(r.text, "xml")
    sitemap_locs = [loc.get_text(strip=True) for loc in soup.select("sitemap > loc")]
    for sm in sitemap_locs:
        try:
            rs = http.get(sm)
        except Exception:
            continue
        doc = BeautifulSoup(rs.text, "xml")
        for url in doc.select("url"):
            loc = url.select_one("loc")
            lastmod = url.select_one("lastmod")
            if not loc:
                continue
            u = loc.get_text(strip=True)
            lm_dt: Optional[datetime] = None
            if lastmod and lastmod.get_text(strip=True):
                try:
                    lm_dt = datetime.fromisoformat(lastmod.get_text(strip=True).replace("Z", "+00:00"))
                except Exception:
                    lm_dt = None
            yield u, lm_dt


def fetch_web_for_issue_week(http: HttpClient, cfg: Settings, issue: Issue) -> List[Article]:
    start = issue.date - timedelta(days=cfg.week_radius_days)
    end = issue.date + timedelta(days=cfg.week_radius_days)

    results: List[Article] = []
    seen: Set[str] = set()

    for url, lastmod in _iter_sitemap_urls(http, cfg):
        if not url.startswith(cfg.base_url):
            continue
        # web-only: exclude magazine namespace
        if "/magazine/" in url:
            continue
        if lastmod is None:
            continue
        if lastmod.date() < start.date() or lastmod.date() > end.date():
            continue
        if url in seen:
            continue
        seen.add(url)

        rr = http.get(url)
        html = rr.text
        text, meta = extract_article_text(html)
        if not text or len(text.split()) < 50:
            try:
                html = http.get_rendered(url)
                text, meta = extract_article_text(html)
            except Exception:
                pass
        # Save raw html
        year = issue.date.year
        slug = slugify(meta.get("title") or url)
        raw_path = os.path.join(cfg.raw_dir, "web", f"year={year}", safe_filename(f"{slug}.html"))
        ensure_parent_dir(raw_path)
        try:
            with open(raw_path, "w", encoding="utf-8") as f:
                f.write(html)
        except Exception:
            pass

        pub_date: Optional[datetime] = None
        if meta.get("date"):
            try:
                pub_date = datetime.fromisoformat(str(meta["date"]).replace("Z", "+00:00"))
            except Exception:
                pub_date = None

        art = Article(
            url=url,
            title=meta.get("title"),
            author=meta.get("author"),
            section=meta.get("section"),
            published=pub_date,
            issue_date=issue.date,
            source="web",
            text=text or "",
        )
        _save_raw_and_extracted(art, cfg)
        results.append(art)

    return results
