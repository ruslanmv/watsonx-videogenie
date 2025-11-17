"""Unit tests for prompt service utilities.

Author: Ruslan Magana (https://ruslanmv.com)
License: Apache 2.0
"""

import pytest
import sys
from pathlib import Path

# Add service to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "services" / "prompt-service" / "app"))

from utils import split_sentences, clean_text, estimate_speaking_time


class TestSplitSentences:
    """Test suite for split_sentences function."""

    def test_basic_splitting(self):
        """Test basic sentence splitting."""
        text = "Hello world! How are you? I am fine."
        result = split_sentences(text)
        assert len(result) == 3
        assert result[0] == "Hello world!"
        assert result[1] == "How are you?"
        assert result[2] == "I am fine."

    def test_empty_string(self):
        """Test with empty string."""
        assert split_sentences("") == []

    def test_single_sentence(self):
        """Test with single sentence."""
        text = "This is a single sentence."
        result = split_sentences(text)
        assert len(result) == 1


class TestCleanText:
    """Test suite for clean_text function."""

    def test_remove_extra_whitespace(self):
        """Test removing extra whitespace."""
        text = "  Hello   world  "
        result = clean_text(text)
        assert result == "Hello world"

    def test_empty_string(self):
        """Test with empty string."""
        assert clean_text("") == ""


class TestEstimateSpeakingTime:
    """Test suite for estimate_speaking_time function."""

    def test_basic_estimation(self):
        """Test basic time estimation."""
        text = "This is a sample sentence with ten words total here."
        time = estimate_speaking_time(text)
        assert isinstance(time, float)
        assert time > 0

    def test_empty_text(self):
        """Test with empty text."""
        assert estimate_speaking_time("") == 0.0
