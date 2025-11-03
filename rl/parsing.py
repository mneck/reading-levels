from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

from bs4 import BeautifulSoup


_BODY_SELECTORS = [
    "article",
    "main",
    "div.article__body",
    "div.ArticleBody__content",
    "section.article-body",
    "div.Body__inner-container",
    "div.body__inner-container",
]


def _collect_paragraphs(el) -> List[str]:
    paras: List[str] = []
    for p in el.select("p"):
        txt = p.get_text(" ", strip=True)
        if txt and len(txt) > 1:
            paras.append(txt)
    return paras


def extract_meta(html: str) -> Dict[str, Optional[str]]:
    soup = BeautifulSoup(html, "lxml")
    meta: Dict[str, Optional[str]] = {
        "title": None,
        "author": None,
        "date": None,
        "section": None,
    }
    # Title
    if soup.title and soup.title.string:
        meta["title"] = soup.title.string.strip()
    og_title = soup.find("meta", attrs={"property": "og:title"})
    if og_title and og_title.get("content"):
        meta["title"] = og_title.get("content").strip()
    # Author
    for sel in [
        "meta[name='author']",
        "a.byline__name",
        "span.byline__name",
        "a[rel='author']",
    ]:
        tag = soup.select_one(sel)
        if tag:
            content = tag.get("content") if tag.name == "meta" else tag.get_text(strip=True)
            if content:
                meta["author"] = content
                break
    # Date
    date_tag = soup.find("meta", attrs={"property": "article:published_time"})
    if date_tag and date_tag.get("content"):
        meta["date"] = date_tag.get("content")
    # Section
    sec = soup.find("meta", attrs={"property": "article:section"})
    if sec and sec.get("content"):
        meta["section"] = sec.get("content")
    if not meta["section"]:
        # try breadcrumbs
        bc = soup.select_one("nav.breadcrumbs a:last-of-type")
        if bc:
            meta["section"] = bc.get_text(strip=True)
    return meta


def extract_article_text(html: str) -> Tuple[str, Dict[str, Optional[str]]]:
    soup = BeautifulSoup(html, "lxml")
    meta = extract_meta(html)

    # Prefer a clear article container
    for sel in _BODY_SELECTORS:
        container = soup.select_one(sel)
        if container:
            paras = _collect_paragraphs(container)
            if len(paras) >= 2:
                return ("\n\n".join(paras), meta)

    # Fallback: all <p> under body
    body = soup.body or soup
    paras = _collect_paragraphs(body)
    return ("\n\n".join(paras), meta)
