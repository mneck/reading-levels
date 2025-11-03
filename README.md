## New Yorker Reading Levels

This project scrapes The New Yorker magazine issues and web-only content, extracts article text, computes readability metrics, and aggregates results by issue and year.

### Features
- Scrape magazine issues (HTML, not PDFs) and web-exclusive content.
- Date alignment: web content within ±3 days of each issue.
- Deduplication: magazine articles excluded from web-only set.
- Readability metrics: Gunning Fog, Dale–Chall, Flesch Reading Ease.
- Per-article, per-issue, and per-year CSV outputs.
- On-disk caching, polite rate limiting, resume capability.
- Optional Playwright fallback for pages requiring JS render.

### Install
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install --with-deps
```

### Authentication (cookies)
Place your exported cookies at `data/ny.json` (recommended), or provide a path via `--cookies`.
- Use a browser extension such as "Export Cookies" to save cookies for `https://www.newyorker.com`.
- The file should contain a list of cookie objects with `name`, `value`, and `domain` fields.
- If `--cookies` is omitted, the CLI auto-detects `data/ny.json`, then `rl/ny.json`, then `cookies.json`.

### Data layout
```
data/
  cache/http/
  raw/{magazine,web}/year=YYYY/
  extracted/{magazine,web}/year=YYYY/
  metrics/
  logs/
```

### CLI usage
```bash
# Fetch magazine issues (2005–2024). Auto-detects cookies at data/ny.json if present
python -m rl.cli fetch-magazine --year-start 2005 --year-end 2024

# Or specify explicitly
python -m rl.cli fetch-magazine --year-start 2005 --year-end 2024 --cookies data/ny.json

# Fetch web-only content aligned to issues (±3 days)
python -m rl.cli fetch-web --year-start 2005 --year-end 2024

# Compute metrics and aggregate
python -m rl.cli compute-metrics --source all
python -m rl.cli aggregate

# Visualize yearly trends
python -m rl.cli visualize
```

### Notes on accuracy
- The project includes native implementations of readability metrics. If `textstat` is installed, metrics may be more accurate.
- Dale–Chall uses an internal common-words list; if `textstat` is present, its implementation is preferred.

### Outliers
Outliers are unusually extreme readability scores caused by very short texts, odd formatting, or extraction noise. By default we keep all data and later show robust aggregates (median, percentiles). You can enable clipping via CLI flags.

### Disclaimer
This project is for research and educational purposes. Respect the site's terms of service and rate limits.
