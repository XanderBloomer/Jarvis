"""Shared test fixtures."""

import pytest
from fastapi.testclient import TestClient

from content_engine.api.main import app


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the FastAPI app."""
    return TestClient(app)
