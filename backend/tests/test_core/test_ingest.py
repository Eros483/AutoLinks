# ----- ingestion logic tests @ backend/tests/test_core/test_ingest.py -----
from backend.core.ingest import build_link_graph, extract_internal_links


def test_extract_internal_links_filters_and_normalizes_same_domain_urls():
    """Test internal links are kept on-domain, deduped, and normalized."""
    html = """
    <html>
      <body>
        <a href="/post-one/">Post One</a>
        <a href="https://example.com/post-two#section">Post Two</a>
        <a href="mailto:test@example.com">Email</a>
        <a href="https://other.com/post-three">External</a>
        <a href="/post-one">Duplicate</a>
      </body>
    </html>
    """

    links = extract_internal_links(html, "https://example.com/source-post/")

    assert links == [
        "https://example.com/post-one",
        "https://example.com/post-two",
    ]


def test_build_link_graph_counts_real_inbound_links():
    """Test inbound counts are built by inverting outbound internal links."""
    crawled_pages = {
        "https://example.com/a": {
            "text": "A",
            "html": "<html></html>",
            "outbound_links": [
                "https://example.com/b",
                "https://example.com/c",
            ],
        },
        "https://example.com/b": {
            "text": "B",
            "html": "<html></html>",
            "outbound_links": ["https://example.com/c"],
        },
        "https://example.com/c": {
            "text": "C",
            "html": "<html></html>",
            "outbound_links": [],
        },
    }

    graph = build_link_graph(crawled_pages)

    assert graph == {
        "https://example.com/a": 0,
        "https://example.com/b": 1,
        "https://example.com/c": 2,
    }
