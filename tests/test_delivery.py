"""Tests for email delivery."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from research_digest.config import AppConfig
from research_digest.models import DigestEntry, Paper
from research_digest.rendering.html_email import render_email


def _entry(rank: int = 1) -> DigestEntry:
    return DigestEntry(
        paper=Paper(
            source="arxiv",
            external_id=f"2401.{rank:05d}",
            title=f"Test Paper {rank}",
            authors=["Alice", "Bob"],
            abstract="Test abstract.",
            categories=["cs.SD"],
            published_at=datetime(2024, 1, 15, tzinfo=timezone.utc),
            canonical_url=f"http://arxiv.org/abs/2401.{rank:05d}",
            pdf_url=f"http://arxiv.org/pdf/2401.{rank:05d}",
        ),
        score=50.0 - rank * 10,
        rank=rank,
        reason="test reason",
        abstract_excerpt="A concise newsletter-style summary.",
    )


class TestHtmlEmail:
    def test_render_basic(self) -> None:
        entries = [_entry(1), _entry(2)]
        cfg = AppConfig()
        html, text = render_email(entries, cfg)
        assert "Test Paper 1" in html
        assert "Test Paper 2" in html
        assert "<html>" in html
        assert "Test Paper 1" in text

    def test_render_empty(self) -> None:
        cfg = AppConfig()
        html, text = render_email([], cfg)
        assert "No papers matched" in html
        assert "No papers matched" in text

    def test_html_contains_links(self) -> None:
        entries = [_entry(1)]
        cfg = AppConfig()
        html, _ = render_email(entries, cfg)
        assert "arxiv.org/abs/" in html
        assert "arxiv.org/pdf/" in html

    def test_html_contains_summary(self) -> None:
        entries = [_entry(1)]
        cfg = AppConfig()
        html, _ = render_email(entries, cfg)
        assert "newsletter-style summary" in html

    def test_html_narrow_layout(self) -> None:
        entries = [_entry(1)]
        cfg = AppConfig()
        html, _ = render_email(entries, cfg)
        assert "max-width:560px" in html

    def test_html_title_is_linked(self) -> None:
        entries = [_entry(1)]
        cfg = AppConfig()
        html, _ = render_email(entries, cfg)
        assert 'href="http://arxiv.org/abs/2401.00001"' in html
        assert "Test Paper 1" in html


class TestGmailProvider:
    def test_missing_from_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("EMAIL_FROM", raising=False)
        monkeypatch.delenv("EMAIL_TO", raising=False)
        monkeypatch.delenv("GMAIL_APP_PASSWORD", raising=False)
        from research_digest.delivery.gmail import GmailProvider
        with pytest.raises(ValueError, match="EMAIL_FROM"):
            GmailProvider()

    def test_missing_password_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("EMAIL_FROM", "test@test.com")
        monkeypatch.setenv("EMAIL_TO", "test@test.com")
        monkeypatch.delenv("GMAIL_APP_PASSWORD", raising=False)
        from research_digest.delivery.gmail import GmailProvider
        with pytest.raises(ValueError, match="GMAIL_APP_PASSWORD"):
            GmailProvider()

    def test_send_calls_smtp(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("EMAIL_FROM", "from@test.com")
        monkeypatch.setenv("EMAIL_TO", "to@test.com")
        monkeypatch.setenv("GMAIL_APP_PASSWORD", "testpass")

        from research_digest.delivery.gmail import GmailProvider

        provider = GmailProvider()

        mock_smtp = MagicMock()
        mock_smtp_instance = MagicMock()
        mock_smtp.__enter__ = MagicMock(return_value=mock_smtp_instance)
        mock_smtp.__exit__ = MagicMock(return_value=False)

        with patch("research_digest.delivery.gmail.smtplib.SMTP", return_value=mock_smtp):
            provider.send("Test Subject", "<h1>HTML</h1>", "Plain text")

        mock_smtp_instance.starttls.assert_called_once()
        mock_smtp_instance.login.assert_called_once_with("from@test.com", "testpass")
        mock_smtp_instance.send_message.assert_called_once()


class TestLatexInEmail:
    def test_greek_converted_in_html_title(self) -> None:
        entry = _entry(1)
        entry.paper = entry.paper.model_copy(update={
            "title": r"Audio Separation using $\beta$-divergence",
        })
        cfg = AppConfig()
        html, text = render_email([entry], cfg)
        assert "\u03b2-divergence" in html
        assert r"$\beta$" not in html
        assert "\u03b2-divergence" in text
        assert r"$\beta$" not in text

    def test_greek_converted_in_abstract_excerpt(self) -> None:
        entry = _entry(1)
        entry.abstract_excerpt = r"Leveraging $\beta$-divergence for improved separation."
        cfg = AppConfig()
        html, text = render_email([entry], cfg)
        assert "\u03b2-divergence" in html
        assert r"$\beta$" not in html
        assert "\u03b2-divergence" in text

    def test_percent_preserved_in_excerpt(self) -> None:
        """LLM summaries with % must not be corrupted."""
        entry = _entry(1)
        entry.abstract_excerpt = "Achieves 95% accuracy on the test set."
        cfg = AppConfig()
        html, text = render_email([entry], cfg)
        assert "95%" in html
        assert "accuracy" in html
        assert "95%" in text

    def test_plain_title_unchanged(self) -> None:
        entry = _entry(1)
        cfg = AppConfig()
        html, text = render_email([entry], cfg)
        assert "Test Paper 1" in html
        assert "Test Paper 1" in text

    def test_superscript_in_title(self) -> None:
        entry = _entry(1)
        entry.paper = entry.paper.model_copy(update={
            "title": r"$L^2$ Regularization for Audio Models",
        })
        cfg = AppConfig()
        html, _ = render_email([entry], cfg)
        assert "L^2 Regularization" in html
        assert r"$L^2$" not in html

    def test_fraction_in_abstract(self) -> None:
        entry = _entry(1)
        entry.abstract_excerpt = r"We use a $\frac{1}{2}$ scaling factor."
        cfg = AppConfig()
        html, _ = render_email([entry], cfg)
        assert "1/2" in html
        assert r"\frac" not in html

    def test_multiple_latex_expressions(self) -> None:
        entry = _entry(1)
        entry.paper = entry.paper.model_copy(update={
            "title": r"$\alpha$-stable Models with $\beta$-VAE",
        })
        entry.abstract_excerpt = r"Combines $\alpha$-stable distributions with $\beta$-VAE."
        cfg = AppConfig()
        html, text = render_email([entry], cfg)
        assert "\u03b1-stable" in html
        assert "\u03b2-VAE" in html
        assert "\u03b1-stable" in text
        assert "\u03b2-VAE" in text

    def test_accented_text_in_abstract(self) -> None:
        entry = _entry(1)
        entry.abstract_excerpt = r"Following Schr\"odinger's approach to quantum systems."
        cfg = AppConfig()
        html, _ = render_email([entry], cfg)
        assert "Schr\u00f6dinger" in html
        assert r'\"o' not in html

    def test_latex_in_title_and_excerpt_together(self) -> None:
        """Both title and excerpt convert in the same entry."""
        entry = _entry(1)
        entry.paper = entry.paper.model_copy(update={
            "title": r"$\beta$-VAE for Music Generation",
        })
        entry.abstract_excerpt = r"Uses $\beta$-VAE with $\lambda$=0.1 for disentangled audio."
        cfg = AppConfig()
        html, text = render_email([entry], cfg)
        # Title converted
        assert "\u03b2-VAE" in html
        assert r"$\beta$" not in html
        # Excerpt converted
        assert "\u03bb" in html  # lambda
        assert r"$\lambda$" not in html

    def test_percent_in_excerpt_with_latex_in_title(self) -> None:
        """Mixed: LaTeX in title, percent in LLM summary."""
        entry = _entry(1)
        entry.paper = entry.paper.model_copy(update={
            "title": r"$\alpha$-GAN for Audio Synthesis",
        })
        entry.abstract_excerpt = "Generates audio samples with 94.2% fidelity score."
        cfg = AppConfig()
        html, _ = render_email([entry], cfg)
        assert "\u03b1-GAN" in html
        assert "94.2%" in html
        assert "fidelity" in html
