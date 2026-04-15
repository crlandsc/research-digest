"""LaTeX-to-Unicode conversion for clean email rendering.

arXiv paper titles and abstracts contain LaTeX math notation ($\\beta$,
$\\frac{1}{2}$, etc.) that renders as raw text in email clients. This
module converts LaTeX to Unicode characters using pylatexenc.
"""

import re

from pylatexenc.latex2text import LatexNodes2Text

_converter = LatexNodes2Text()


def latex_to_unicode(text: str | None) -> str:
    """Convert LaTeX notation in text to Unicode characters.

    Handles Greek letters, math operators, accents, fractions, and
    sub/superscripts. Unknown macros pass through as-is. Never raises
    on malformed input.

    Special handling:
    - Bare % is escaped before conversion (LaTeX treats % as comment char,
      which would silently eat text like "95% accuracy" -> "95").
    - Display math whitespace is normalized ($$...$$ introduces newlines).
    """
    if not text:
        return ""
    try:
        # Escape bare % that aren't already escaped as \%
        # (LaTeX treats % as comment-to-end-of-line)
        escaped = re.sub(r"(?<!\\)%", r"\\%", text)
        result = _converter.latex_to_text(escaped)
        # Normalize whitespace (display math can introduce newlines/indentation)
        return " ".join(result.split())
    except Exception:
        return text
