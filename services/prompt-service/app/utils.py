"""Text Processing Utilities.

Utility functions for text manipulation and sentence splitting.
Can be extended with spaCy or other NLP libraries for advanced processing.

Author: Ruslan Magana (https://ruslanmv.com)
License: Apache 2.0
"""

import re
from typing import List


def split_sentences(text: str) -> List[str]:
    """Split text into individual sentences using regex.

    Splits on punctuation marks (., !, ?) followed by whitespace.
    This is a simple regex-based approach suitable for basic use cases.
    For production with complex text, consider using spaCy or NLTK.

    Args:
        text: Input text to split into sentences.

    Returns:
        List of sentence strings, with empty sentences filtered out.

    Example:
        >>> text = "Hello world! How are you? I am fine."
        >>> sentences = split_sentences(text)
        >>> print(sentences)
        ['Hello world!', 'How are you?', 'I am fine.']

    Note:
        For more sophisticated sentence boundary detection, replace with:
        ```python
        import spacy
        nlp = spacy.load("en_core_web_sm")
        doc = nlp(text)
        return [sent.text.strip() for sent in doc.sents]
        ```
    """
    if not text or not isinstance(text, str):
        return []

    # Strip leading/trailing whitespace
    text = text.strip()

    # Split on punctuation followed by whitespace
    # Pattern: (?<=[.!?]) matches position after punctuation
    # \s+ matches one or more whitespace characters
    sentences = re.split(r"(?<=[.!?])\s+", text)

    # Filter out empty strings and whitespace-only strings
    sentences = [s.strip() for s in sentences if s and s.strip()]

    return sentences


def clean_text(text: str) -> str:
    """Clean and normalize text for processing.

    Removes extra whitespace, normalizes line breaks, and trims content.

    Args:
        text: Raw input text.

    Returns:
        Cleaned and normalized text.

    Example:
        >>> text = "  Hello\\n\\n  world!  \\n"
        >>> clean_text(text)
        'Hello world!'
    """
    if not text:
        return ""

    # Replace multiple whitespace with single space
    text = re.sub(r"\s+", " ", text)

    # Remove leading/trailing whitespace
    text = text.strip()

    return text


def estimate_speaking_time(
    text: str,
    words_per_minute: int = 150,
) -> float:
    """Estimate speaking time for given text.

    Calculates approximate time needed to speak the text at normal pace.
    Average speaking rate is typically 125-150 words per minute.

    Args:
        text: Input text to estimate.
        words_per_minute: Speaking rate (default: 150 WPM).

    Returns:
        Estimated speaking time in seconds.

    Example:
        >>> text = "This is a sample sentence with ten words total."
        >>> time = estimate_speaking_time(text)
        >>> print(f"{time:.1f} seconds")
        '4.0 seconds'
    """
    if not text:
        return 0.0

    # Count words (split on whitespace)
    word_count = len(text.split())

    # Calculate time in seconds
    time_seconds = (word_count / words_per_minute) * 60

    return round(time_seconds, 2)
