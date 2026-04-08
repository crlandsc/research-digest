"""Extractive summarization for the MVP pipeline."""


def extractive_summary(abstract: str, max_sentences: int = 3) -> str:
    """Extract the first N sentences from an abstract."""
    if not abstract:
        return ""
    sentences = abstract.split(". ")
    if len(sentences) <= max_sentences:
        return abstract
    return ". ".join(sentences[:max_sentences]) + "."
