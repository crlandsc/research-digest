"""arXiv category code to human-readable name mapping."""

ARXIV_CATEGORIES: dict[str, str] = {
    # Computer Science
    "cs.AI": "Artificial Intelligence",
    "cs.CL": "Computation & Language",
    "cs.CV": "Computer Vision",
    "cs.IR": "Information Retrieval",
    "cs.LG": "Machine Learning",
    "cs.MM": "Multimedia",
    "cs.NE": "Neural & Evolutionary Computing",
    "cs.SD": "Sound",
    "cs.CE": "Computational Engineering",
    "cs.CY": "Computers & Society",
    "cs.ET": "Emerging Technologies",
    # Electrical Engineering
    "eess.AS": "Audio & Speech Processing",
    "eess.SP": "Signal Processing",
    # Statistics
    "stat.ML": "Machine Learning (Stats)",
    # Quantitative Biology
    "q-bio.NC": "Neurons & Cognition",
}


def category_label(code: str) -> str:
    """Return 'cs.SD (Sound)' style label, or just the code if unknown."""
    name = ARXIV_CATEGORIES.get(code)
    return f"{code} ({name})" if name else code
