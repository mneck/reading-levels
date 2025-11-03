from __future__ import annotations

import json
import os
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Iterable, List, Optional, Tuple

from .config import Settings
from .metrics import readability_metrics
from .utils import ensure_parent_dir, iso_date, write_csv


@dataclass
class ArticleRow:
    source: str
    url: str
    title: Optional[str]
    author: Optional[str]
    section: Optional[str]
    published: Optional[str]
    issue_date: Optional[str]
    num_words: int
    num_sentences: int
    gunning_fog: Optional[float]
    dale_chall: Optional[float]
    flesch_reading_ease: Optional[float]


def _iter_extracted_json(cfg: Settings, source: str) -> Iterable[Dict[str, object]]:
    base = os.path.join(cfg.extracted_dir, source)
    if not os.path.exists(base):
        return
    for root, _, files in os.walk(base):
        for fn in files:
            if not fn.endswith(".json"):
                continue
            path = os.path.join(root, fn)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                yield data
            except Exception:
                continue


def compute_per_article(cfg: Settings) -> List[ArticleRow]:
    rows: List[ArticleRow] = []
    for source in ("magazine", "web"):
        for data in _iter_extracted_json(cfg, source):
            text = str(data.get("text", ""))
            m = readability_metrics(text)
            rows.append(
                ArticleRow(
                    source=source,
                    url=str(data.get("url")),
                    title=(data.get("title") or None),
                    author=(data.get("author") or None),
                    section=(data.get("section") or None),
                    published=(data.get("published") or None),
                    issue_date=(data.get("issue_date") or None),
                    num_words=int(m.get("num_words") or 0),
                    num_sentences=int(m.get("num_sentences") or 0),
                    gunning_fog=(m.get("gunning_fog") if m.get("gunning_fog") is not None else None),
                    dale_chall=(m.get("dale_chall") if m.get("dale_chall") is not None else None),
                    flesch_reading_ease=(m.get("flesch_reading_ease") if m.get("flesch_reading_ease") is not None else None),
                )
            )
    return rows


def write_per_article_csv(cfg: Settings, rows: List[ArticleRow]) -> str:
    out = os.path.join(cfg.metrics_dir, "per_article.csv")
    fieldnames = [
        "source",
        "url",
        "title",
        "author",
        "section",
        "published",
        "issue_date",
        "num_words",
        "num_sentences",
        "gunning_fog",
        "dale_chall",
        "flesch_reading_ease",
    ]
    write_csv(out, (r.__dict__ for r in rows), fieldnames)
    return out


def _mean(values: List[float]) -> Optional[float]:
    vals = [v for v in values if v is not None]
    if not vals:
        return None
    return sum(vals) / len(vals)


def _weighted_mean(values: List[Tuple[Optional[float], int]]) -> Optional[float]:
    num = 0.0
    den = 0
    for val, w in values:
        if val is None or w <= 0:
            continue
        num += val * w
        den += w
    if den == 0:
        return None
    return num / den


def aggregate_per_issue(cfg: Settings, rows: List[ArticleRow]) -> str:
    # Group by issue_date + source
    by_issue: Dict[Tuple[str, str], List[ArticleRow]] = defaultdict(list)
    for r in rows:
        key_date = r.issue_date or r.published or None
        if not key_date:
            continue
        by_issue[(key_date, r.source)].append(r)

    out_rows: List[Dict[str, object]] = []
    for (issue_date, source), items in sorted(by_issue.items()):
        g = _mean([r.gunning_fog for r in items])
        d = _mean([r.dale_chall for r in items])
        f = _mean([r.flesch_reading_ease for r in items])
        gw = _weighted_mean([(r.gunning_fog, r.num_words) for r in items])
        dw = _weighted_mean([(r.dale_chall, r.num_words) for r in items])
        fw = _weighted_mean([(r.flesch_reading_ease, r.num_words) for r in items])
        total_words = sum(r.num_words for r in items)
        out_rows.append({
            "issue_date": issue_date,
            "source": source,
            "num_articles": len(items),
            "total_words": total_words,
            "gunning_fog_mean": g,
            "dale_chall_mean": d,
            "flesch_reading_ease_mean": f,
            "gunning_fog_weighted_mean": gw,
            "dale_chall_weighted_mean": dw,
            "flesch_reading_ease_weighted_mean": fw,
        })

    out = os.path.join(cfg.metrics_dir, "per_issue.csv")
    fieldnames = list(out_rows[0].keys()) if out_rows else [
        "issue_date","source","num_articles","total_words",
        "gunning_fog_mean","dale_chall_mean","flesch_reading_ease_mean",
        "gunning_fog_weighted_mean","dale_chall_weighted_mean","flesch_reading_ease_weighted_mean"
    ]
    write_csv(out, out_rows, fieldnames)
    return out


def aggregate_per_year(cfg: Settings, per_issue_csv_path: str) -> str:
    # Read per_issue CSV
    import csv

    by_year: Dict[Tuple[int, str], List[Dict[str, float]]] = defaultdict(list)
    with open(per_issue_csv_path, "r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            date = datetime.strptime(row["issue_date"], "%Y-%m-%d")
            year = date.year
            source = row["source"]
            by_year[(year, source)].append({
                "gunning_fog": float(row["gunning_fog_mean"]) if row["gunning_fog_mean"] else None,
                "dale_chall": float(row["dale_chall_mean"]) if row["dale_chall_mean"] else None,
                "flesch": float(row["flesch_reading_ease_mean"]) if row["flesch_reading_ease_mean"] else None,
            })

    out_rows: List[Dict[str, object]] = []
    for (year, source), items in sorted(by_year.items()):
        g = _mean([x["gunning_fog"] for x in items])
        d = _mean([x["dale_chall"] for x in items])
        f = _mean([x["flesch"] for x in items])
        out_rows.append({
            "year": year,
            "source": source,
            "gunning_fog_mean": g,
            "dale_chall_mean": d,
            "flesch_reading_ease_mean": f,
        })

    out = os.path.join(cfg.metrics_dir, "per_year.csv")
    fieldnames = ["year","source","gunning_fog_mean","dale_chall_mean","flesch_reading_ease_mean"]
    write_csv(out, out_rows, fieldnames)
    return out
