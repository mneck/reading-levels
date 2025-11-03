import types

from rl.ny_scraper import _ISSUE_LINK_RE, _MAG_ARTICLE_RE, get_issue_articles
from rl.config import Settings


class FakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text
        self.status_code = 200


class FakeHttp:
    def __init__(self, html_by_url):
        self.html_by_url = html_by_url

    def get(self, url: str):
        return FakeResponse(self.html_by_url.get(url, ""))


def test_regex_patterns_match_expected_urls():
    assert _ISSUE_LINK_RE.match("/magazine/2024/01/01")
    assert _ISSUE_LINK_RE.match("/magazine/2024/12/31/")
    assert _MAG_ARTICLE_RE.match("/magazine/2024/01/01/an-article-slug")
    assert _MAG_ARTICLE_RE.match("/magazine/2024/01/01/an-article-slug/")


def test_get_issue_articles_parses_links():
    cfg = Settings()
    issue_url = f"{cfg.base_url}/magazine/2024/01/01"
    html = """
    <html><body>
      <a href="/magazine/2024/01/01/an-article-slug">A</a>
      <a href="/magazine/2024/01/01/another-article">B</a>
      <a href="/news/something-else">C</a>
    </body></html>
    """
    http = FakeHttp({issue_url: html})
    urls = get_issue_articles(http, cfg, issue_url)
    assert any(u.endswith("/magazine/2024/01/01/an-article-slug") for u in urls)
    assert any(u.endswith("/magazine/2024/01/01/another-article") for u in urls)
    assert all("/news/" not in u for u in urls)
