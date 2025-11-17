"""Pytest configuration and fixtures.

Author: Ruslan Magana (https://ruslanmv.com)
License: Apache 2.0
"""

import pytest


@pytest.fixture
def sample_text():
    """Fixture providing sample text for testing."""
    return "Hello world! This is a test. How are you?"


@pytest.fixture
def mock_job_payload():
    """Fixture providing mock job payload."""
    return {
        "jobId": "test-123",
        "text": "Sample text for testing",
        "avatar": "test_avatar"
    }
