from __future__ import annotations

import argparse
import csv
import os
from datetime import datetime

from .aggregation import aggregate_per_issue, aggregate_per_year, compute_per_article, write_per_article_csv
from .config import Settings, ensure_dirs, load_cookies, find_default_cookies
from .http import HttpClient
from .ny_scraper import Issue, fetch_magazine_issue, fetch_web_for_issue_week, get_issues_for_year


def cmd_fetch_magazine(args) -> None:
    cfg = Settings()
    ensure_dirs(cfg)
    cookies_path = args.cookies or find_default_cookies()
    cookies = load_cookies(cookies_path) if cookies_path else []
    http = HttpClient(cfg, cookies=cookies)

    issues_log_path = os.path.join(cfg.logs_dir, "issues_log.csv")
    os.makedirs(cfg.logs_dir, exist_ok=True)
    if not os.path.exists(issues_log_path):
        with open(issues_log_path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["issue_date", "issue_url", "num_articles"])

    for year in range(args.year_start, args.year_end + 1):
        issues = get_issues_for_year(http, cfg, year)
        for issue in issues:
            arts = fetch_magazine_issue(http, cfg, issue)
            with open(issues_log_path, "a", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow([issue.date.strftime("%Y-%m-%d"), issue.url, len(arts)])


def cmd_fetch_web(args) -> None:
    cfg = Settings()
    ensure_dirs(cfg)
    cookies_path = args.cookies or find_default_cookies()
    cookies = load_cookies(cookies_path) if cookies_path else []
    http = HttpClient(cfg, cookies=cookies)

    for year in range(args.year_start, args.year_end + 1):
        issues = get_issues_for_year(http, cfg, year)
        for issue in issues:
            fetch_web_for_issue_week(http, cfg, issue)


def cmd_compute_metrics(args) -> None:
    cfg = Settings()
    ensure_dirs(cfg)
    rows = compute_per_article(cfg)
    out = write_per_article_csv(cfg, rows)
    print(f"wrote per-article metrics: {out}")


def cmd_aggregate(args) -> None:
    cfg = Settings()
    ensure_dirs(cfg)
    # per-issue
    rows = compute_per_article(cfg)
    per_article = write_per_article_csv(cfg, rows)
    per_issue = aggregate_per_issue(cfg, rows)
    per_year = aggregate_per_year(cfg, per_issue)
    print(f"wrote: {per_article}\n{per_issue}\n{per_year}")


def cmd_visualize(args) -> None:
    import csv
    import matplotlib.pyplot as plt

    cfg = Settings()
    per_year_path = os.path.join(cfg.metrics_dir, "per_year.csv")
    data = {"magazine": [], "web": []}
    with open(per_year_path, "r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            source = row["source"]
            year = int(row["year"]) 
            g = float(row["gunning_fog_mean"]) if row["gunning_fog_mean"] else None
            d = float(row["dale_chall_mean"]) if row["dale_chall_mean"] else None
            f_re = float(row["flesch_reading_ease_mean"]) if row["flesch_reading_ease_mean"] else None
            data[source].append((year, g, d, f_re))

    plt.figure(figsize=(10,6))
    for source, series in data.items():
        series.sort(key=lambda x: x[0])
        years = [x[0] for x in series]
        gvals = [x[1] for x in series]
        dvals = [x[2] for x in series]
        fvals = [x[3] for x in series]
        plt.plot(years, gvals, label=f"Gunning Fog ({source})")
        plt.plot(years, dvals, label=f"Dale–Chall ({source})")
        plt.plot(years, fvals, label=f"Flesch Reading Ease ({source})")

    plt.title("New Yorker Readability by Year (Magazine vs Web)")
    plt.xlabel("Year")
    plt.ylabel("Score (higher=flesch easier; others harder)")
    plt.legend()
    out_path = os.path.join(cfg.metrics_dir, "yearly_trends.png")
    ensure_dirs(cfg)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    print(f"wrote visualization: {out_path}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="rl", description="New Yorker reading levels pipeline")
    sub = p.add_subparsers(dest="command", required=True)

    fm = sub.add_parser("fetch-magazine", help="Fetch magazine issues and articles")
    fm.add_argument("--year-start", type=int, required=True)
    fm.add_argument("--year-end", type=int, required=True)
    fm.add_argument("--cookies", type=str, default=None, help="Path to cookies.json (default: auto-detect)")
    fm.set_defaults(func=cmd_fetch_magazine)

    fw = sub.add_parser("fetch-web", help="Fetch web-only content aligned to issues (±3 days)")
    fw.add_argument("--year-start", type=int, required=True)
    fw.add_argument("--year-end", type=int, required=True)
    fw.add_argument("--cookies", type=str, default=None, help="Path to cookies.json (default: auto-detect)")
    fw.set_defaults(func=cmd_fetch_web)

    cm = sub.add_parser("compute-metrics", help="Compute per-article metrics")
    cm.add_argument("--source", choices=["magazine","web","all"], default="all")
    cm.set_defaults(func=cmd_compute_metrics)

    ag = sub.add_parser("aggregate", help="Aggregate per-issue and per-year metrics")
    ag.set_defaults(func=cmd_aggregate)

    vz = sub.add_parser("visualize", help="Create yearly trend visualization")
    vz.set_defaults(func=cmd_visualize)

    return p


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
