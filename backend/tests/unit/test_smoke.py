"""Bootstrap smoke test — proves pytest, pytest-cov, and CI are wired up correctly."""

from app import __version__


def test_version_is_defined():
    assert __version__ == "0.1.0"
