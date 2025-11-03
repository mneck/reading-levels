import os

from rl.utils import sha1_hex, slugify
from rl.metrics import readability_metrics
from rl.parsing import extract_article_text, extract_meta


def test_sha1_hex_and_slugify():
    assert sha1_hex("hello") == "aaf4c61ddcc5e8a2dabede0f3b482cd9aea9434d"
    assert slugify("Hello, World!") == "hello-world"
    assert slugify("  ") == "untitled"


def test_readability_metrics_basic():
    text = "The cat sat on the mat. It was sunny."
    m = readability_metrics(text)
    assert m["num_words"] >= 6
    assert m["num_sentences"] >= 2
    # All metrics should be numbers (not None) for non-empty text
    assert m["gunning_fog"] is not None
    assert m["dale_chall"] is not None
    assert m["flesch_reading_ease"] is not None


def test_parsing_extracts_title_and_text():
    html = """
    <html>
      <head>
        <title>Sample Article</title>
        <meta property="article:published_time" content="2024-01-01T00:00:00Z" />
        <meta property="article:section" content="Fiction" />
      </head>
      <body>
        <article>
          <p>First paragraph.</p>
          <p>Second paragraph.</p>
        </article>
      </body>
    </html>
    """
    text, meta = extract_article_text(html)
    assert "First paragraph." in text
    assert "Second paragraph." in text
    assert meta["title"] == "Sample Article"
    assert meta["section"] == "Fiction"
    assert meta["date"] == "2024-01-01T00:00:00Z"
