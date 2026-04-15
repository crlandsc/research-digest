"""Tests for LaTeX-to-Unicode conversion."""

import pytest

from research_digest.rendering.latex import latex_to_unicode


class TestLatexToUnicode:
    """Test latex_to_unicode() on patterns common in arXiv metadata."""

    # --- Greek letters (most common in arXiv titles/abstracts) ---

    def test_beta(self) -> None:
        assert latex_to_unicode(r"$\beta$-divergence") == "\u03b2-divergence"

    def test_alpha(self) -> None:
        assert latex_to_unicode(r"$\alpha$") == "\u03b1"

    def test_uppercase_omega(self) -> None:
        assert latex_to_unicode(r"$\Omega$") == "\u03a9"

    def test_multiple_greek(self) -> None:
        assert latex_to_unicode(r"$\alpha$ and $\beta$ values") == "\u03b1 and \u03b2 values"

    def test_pi(self) -> None:
        assert latex_to_unicode(r"$\pi$") == "\u03c0"

    # --- Superscripts and subscripts (pylatexenc v2 keeps ASCII ^ and _) ---

    def test_superscript(self) -> None:
        assert latex_to_unicode(r"$L^2$ norm") == "L^2 norm"

    def test_subscript(self) -> None:
        assert latex_to_unicode(r"$x_i$") == "x_i"

    def test_big_o_notation(self) -> None:
        assert latex_to_unicode(r"$O(n^2)$") == "O(n^2)"

    # --- Math operators and relations ---

    def test_leq(self) -> None:
        assert latex_to_unicode(r"$x \leq y$") == "x \u2264 y"

    def test_geq(self) -> None:
        assert latex_to_unicode(r"$x \geq y$") == "x \u2265 y"

    def test_nabla(self) -> None:
        assert latex_to_unicode(r"$\nabla f$") == "\u2207 f"

    def test_times(self) -> None:
        assert latex_to_unicode(r"$\times$") == "\u00d7"

    def test_approx(self) -> None:
        assert latex_to_unicode(r"$\approx$") == "\u2248"

    def test_rightarrow(self) -> None:
        assert latex_to_unicode(r"$\rightarrow$") == "\u2192"

    def test_infty(self) -> None:
        assert latex_to_unicode(r"$\infty$") == "\u221e"

    def test_in_set(self) -> None:
        assert latex_to_unicode(r"$\in$") == "\u2208"

    # --- Fractions ---

    def test_simple_fraction(self) -> None:
        assert latex_to_unicode(r"$\frac{1}{2}$") == "1/2"

    def test_nested_fraction(self) -> None:
        result = latex_to_unicode(r"$\frac{\alpha}{\beta+1}$")
        assert "\u03b1" in result
        assert "\u03b2" in result

    # --- Accented characters ---

    def test_umlaut(self) -> None:
        assert latex_to_unicode(r'Schr\"odinger') == "Schr\u00f6dinger"

    def test_acute(self) -> None:
        assert latex_to_unicode(r"R\'enyi") == "R\u00e9nyi"

    # --- Calligraphic / blackboard bold ---

    def test_mathcal(self) -> None:
        assert latex_to_unicode(r"$\mathcal{L}$") == "\u2112"

    def test_mathbb(self) -> None:
        assert latex_to_unicode(r"$\mathbb{R}$") == "\u211d"

    # --- Percent handling (CRITICAL: % is LaTeX comment char) ---

    def test_bare_percent_preserved(self) -> None:
        """Bare % in text (e.g., LLM summaries) must not be eaten."""
        assert latex_to_unicode("95% accuracy") == "95% accuracy"

    def test_multiple_percents(self) -> None:
        text = "10% over baseline and 5% margin"
        assert latex_to_unicode(text) == text

    def test_percent_with_latex(self) -> None:
        result = latex_to_unicode(r"with $\beta$ at 95% level")
        assert "\u03b2" in result
        assert "95%" in result
        assert "level" in result

    def test_already_escaped_percent(self) -> None:
        assert latex_to_unicode(r"improves by 5\%") == "improves by 5%"

    def test_llm_summary_with_percent(self) -> None:
        text = "Achieves state-of-the-art 92.3% accuracy on AudioSet."
        assert latex_to_unicode(text) == text

    # --- Plain text passthrough ---

    def test_plain_text_unchanged(self) -> None:
        text = "Audio Source Separation in Reverberant Environments"
        assert latex_to_unicode(text) == text

    def test_empty_string(self) -> None:
        assert latex_to_unicode("") == ""

    def test_none_returns_empty(self) -> None:
        assert latex_to_unicode(None) == ""

    # --- Whitespace normalization ---

    def test_display_math_whitespace_normalized(self) -> None:
        """Display math ($$...$$) introduces newlines; we normalize them."""
        assert latex_to_unicode(r"$$\beta$$") == "\u03b2"

    # --- Mixed content (realistic arXiv patterns) ---

    def test_mixed_latex_and_text(self) -> None:
        text = r"Using $\beta$-divergence based Nonnegative Factorization"
        expected = "Using \u03b2-divergence based Nonnegative Factorization"
        assert latex_to_unicode(text) == expected

    def test_k_nearest_neighbors(self) -> None:
        assert latex_to_unicode(r"$k$-nearest neighbors") == "k-nearest neighbors"

    def test_f_divergence(self) -> None:
        assert latex_to_unicode(r"Learning $f$-Divergences") == "Learning f-Divergences"

    # --- Edge cases ---

    def test_already_unicode(self) -> None:
        text = "already has \u03b2 and \u03b1"
        assert latex_to_unicode(text) == text

    def test_complex_expression_degrades_gracefully(self) -> None:
        result = latex_to_unicode(r"$\sum_{i=1}^{N} x_i$")
        assert isinstance(result, str)
        assert len(result) > 0
        assert "\u2211" in result  # sum symbol

    def test_malformed_latex_does_not_crash(self) -> None:
        result = latex_to_unicode(r"unclosed $\beta math")
        assert isinstance(result, str)
        assert "\u03b2" in result
