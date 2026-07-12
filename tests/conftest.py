from __future__ import annotations

import os
from pathlib import Path

import pytest

from tests.fixtures.build_fixtures import build_all


@pytest.fixture(scope="session", autouse=True)
def deterministic_test_environment() -> None:
    os.environ.setdefault("WHO_IS_ADAM_OFFLINE", "1")
    os.environ.setdefault("WHO_IS_ADAM_FIXED_TIMESTAMP", "2026-07-12T00:00:00Z")
    os.environ.setdefault("PYTHONHASHSEED", "0")
    build_all()


@pytest.fixture(scope="session")
def pdf_fixtures() -> Path:
    return Path(__file__).resolve().parent / "fixtures" / "pdfs"
