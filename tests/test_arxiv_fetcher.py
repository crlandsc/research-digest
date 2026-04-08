"""Tests for arXiv fetcher and XML parsing."""

from datetime import datetime, timedelta, timezone

import pytest

from research_digest.config import ArxivSourceConfig
from research_digest.fetchers.arxiv import (
    _extract_code_url,
    build_query,
    compute_date_range,
    parse_arxiv_response,
)

SAMPLE_FEED = """\
<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/"
      xmlns:arxiv="http://arxiv.org/schemas/atom">
  <title>ArXiv Query</title>
  <opensearch:totalResults>2</opensearch:totalResults>
  <opensearch:startIndex>0</opensearch:startIndex>
  <opensearch:itemsPerPage>2</opensearch:itemsPerPage>
  <entry>
    <id>http://arxiv.org/abs/2401.12345v2</id>
    <published>2024-01-15T18:00:00Z</published>
    <updated>2024-01-16T09:00:00Z</updated>
    <title>Music Generation with
    Diffusion Models</title>
    <summary>We present a novel approach to music generation using
    diffusion models. Our method achieves state-of-the-art results.</summary>
    <author><name>Alice Smith</name></author>
    <author><name>Bob Jones</name></author>
    <category term="cs.SD" scheme="http://arxiv.org/schemas/atom"/>
    <category term="cs.AI" scheme="http://arxiv.org/schemas/atom"/>
    <arxiv:primary_category term="cs.SD" scheme="http://arxiv.org/schemas/atom"/>
    <link href="http://arxiv.org/abs/2401.12345v2" rel="alternate" type="text/html"/>
    <link href="http://arxiv.org/pdf/2401.12345v2" rel="related" title="pdf" type="application/pdf"/>
  </entry>
  <entry>
    <id>http://arxiv.org/abs/cs/0601001v1</id>
    <published>2006-01-01T12:00:00Z</published>
    <updated>2006-01-01T12:00:00Z</updated>
    <title>Audio Classification Techniques</title>
    <summary>A study of audio classification approaches.</summary>
    <author><name>Carol Davis</name></author>
    <category term="cs.SD" scheme="http://arxiv.org/schemas/atom"/>
    <link href="http://arxiv.org/abs/cs/0601001v1" rel="alternate" type="text/html"/>
  </entry>
</feed>
"""

ERROR_FEED = """\
<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">
  <opensearch:totalResults>1</opensearch:totalResults>
  <entry>
    <id>http://arxiv.org/api/errors#incorrect_id_format_for_1234</id>
    <title>Error</title>
    <summary>incorrect id format for 1234</summary>
  </entry>
</feed>
"""

FEED_WITH_CODE = """\
<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/"
      xmlns:arxiv="http://arxiv.org/schemas/atom">
  <opensearch:totalResults>1</opensearch:totalResults>
  <entry>
    <id>http://arxiv.org/abs/2401.55555v1</id>
    <published>2024-01-15T00:00:00Z</published>
    <updated>2024-01-15T00:00:00Z</updated>
    <title>Audio Model with Code</title>
    <summary>We release our code.</summary>
    <author><name>Alice</name></author>
    <category term="cs.SD"/>
    <arxiv:comment>10 pages; code available at https://github.com/alice/audio-model</arxiv:comment>
    <link href="http://arxiv.org/abs/2401.55555v1" rel="alternate"/>
  </entry>
</feed>
"""

EMPTY_FEED = """\
<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">
  <opensearch:totalResults>0</opensearch:totalResults>
</feed>
"""


class TestParseArxivResponse:
    def test_extracts_correct_count(self) -> None:
        papers, total = parse_arxiv_response(SAMPLE_FEED)
        assert len(papers) == 2
        assert total == 2

    def test_extracts_new_style_id(self) -> None:
        papers, _ = parse_arxiv_response(SAMPLE_FEED)
        assert papers[0].external_id == "2401.12345"

    def test_extracts_old_style_id(self) -> None:
        papers, _ = parse_arxiv_response(SAMPLE_FEED)
        assert papers[1].external_id == "cs/0601001"

    def test_normalizes_title_whitespace(self) -> None:
        papers, _ = parse_arxiv_response(SAMPLE_FEED)
        assert papers[0].title == "Music Generation with Diffusion Models"

    def test_normalizes_abstract_whitespace(self) -> None:
        papers, _ = parse_arxiv_response(SAMPLE_FEED)
        assert "\n" not in papers[0].abstract
        assert "  " not in papers[0].abstract

    def test_extracts_authors(self) -> None:
        papers, _ = parse_arxiv_response(SAMPLE_FEED)
        assert papers[0].authors == ["Alice Smith", "Bob Jones"]
        assert papers[1].authors == ["Carol Davis"]

    def test_extracts_categories(self) -> None:
        papers, _ = parse_arxiv_response(SAMPLE_FEED)
        assert papers[0].categories == ["cs.SD", "cs.AI"]

    def test_extracts_pdf_url(self) -> None:
        papers, _ = parse_arxiv_response(SAMPLE_FEED)
        assert papers[0].pdf_url == "http://arxiv.org/pdf/2401.12345v2"
        assert papers[1].pdf_url is None

    def test_extracts_published_datetime(self) -> None:
        papers, _ = parse_arxiv_response(SAMPLE_FEED)
        assert papers[0].published_at == datetime(2024, 1, 15, 18, 0, 0, tzinfo=timezone.utc)

    def test_extracts_updated_datetime(self) -> None:
        papers, _ = parse_arxiv_response(SAMPLE_FEED)
        assert papers[0].updated_at == datetime(2024, 1, 16, 9, 0, 0, tzinfo=timezone.utc)

    def test_sets_source_arxiv(self) -> None:
        papers, _ = parse_arxiv_response(SAMPLE_FEED)
        assert all(p.source == "arxiv" for p in papers)

    def test_sets_canonical_url(self) -> None:
        papers, _ = parse_arxiv_response(SAMPLE_FEED)
        assert papers[0].canonical_url == "http://arxiv.org/abs/2401.12345v2"

    def test_skips_error_entries(self) -> None:
        papers, _ = parse_arxiv_response(ERROR_FEED)
        assert papers == []

    def test_empty_results(self) -> None:
        papers, total = parse_arxiv_response(EMPTY_FEED)
        assert papers == []
        assert total == 0


class TestCodeUrlExtraction:
    def test_extracts_from_comment(self) -> None:
        papers, _ = parse_arxiv_response(FEED_WITH_CODE)
        assert papers[0].code_url == "https://github.com/alice/audio-model"

    def test_no_code_url(self) -> None:
        papers, _ = parse_arxiv_response(SAMPLE_FEED)
        assert papers[0].code_url is None
        assert papers[1].code_url is None

    def test_extract_github_url(self) -> None:
        assert _extract_code_url("Code at https://github.com/user/repo") == "https://github.com/user/repo"

    def test_extract_gitlab_url(self) -> None:
        assert _extract_code_url("See https://gitlab.com/user/project for code") == "https://gitlab.com/user/project"

    def test_extract_from_abstract(self) -> None:
        assert _extract_code_url("No code here", "Available at https://github.com/org/tool") == "https://github.com/org/tool"

    def test_no_url_returns_none(self) -> None:
        assert _extract_code_url("No URLs here", "Nothing here either") is None

    def test_strips_trailing_period(self) -> None:
        assert _extract_code_url("Code: https://github.com/user/repo.") == "https://github.com/user/repo"


class TestBuildQuery:
    def _cfg(self, **kwargs) -> ArxivSourceConfig:
        return ArxivSourceConfig(**kwargs)

    def test_categories_only(self) -> None:
        q = build_query(
            self._cfg(categories=["cs.SD", "eess.AS"]),
            datetime(2024, 1, 1, tzinfo=timezone.utc),
            datetime(2024, 1, 8, tzinfo=timezone.utc),
        )
        assert "cat:cs.SD OR cat:eess.AS" in q
        assert "all:" not in q
        assert "submittedDate:" in q

    def test_keywords_only(self) -> None:
        q = build_query(
            self._cfg(keyword_queries=["music generation"]),
            datetime(2024, 1, 1, tzinfo=timezone.utc),
            datetime(2024, 1, 8, tzinfo=timezone.utc),
        )
        assert 'all:"music generation"' in q
        assert "cat:" not in q

    def test_categories_and_keywords(self) -> None:
        q = build_query(
            self._cfg(categories=["cs.SD"], keyword_queries=["audio"]),
            datetime(2024, 1, 1, tzinfo=timezone.utc),
            datetime(2024, 1, 8, tzinfo=timezone.utc),
        )
        assert "cat:cs.SD" in q
        assert 'all:"audio"' in q
        assert " AND " in q

    def test_date_range_format(self) -> None:
        q = build_query(
            self._cfg(categories=["cs.SD"]),
            datetime(2024, 1, 1, 6, 0, tzinfo=timezone.utc),
            datetime(2024, 1, 8, 18, 30, tzinfo=timezone.utc),
        )
        assert "submittedDate:[202401010600 TO 202401081830]" in q


class TestComputeDateRange:
    def test_lookback_with_buffer(self) -> None:
        start, end = compute_date_range(7)
        expected_start = end - timedelta(days=8)  # 7 + 1 buffer
        assert abs((start - expected_start).total_seconds()) < 1

    def test_since_last_run(self) -> None:
        last = datetime(2024, 1, 10, 12, 0, 0, tzinfo=timezone.utc)
        start, end = compute_date_range(7, since_last_run=last)
        assert start == last
        assert end.tzinfo == timezone.utc
