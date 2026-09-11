"""Unit tests for the session factory — no real database needed.

create_engine()/sessionmaker() are lazy: neither connects until a query
runs, so these can be tested without a live Postgres.
"""

from unittest.mock import MagicMock

import pytest

import app.db.session as session_module


def _reset_module_state():
    session_module._engine = None
    session_module._SessionLocal = None


class TestGetEngine:
    def setup_method(self):
        _reset_module_state()

    def teardown_method(self):
        _reset_module_state()

    def test_returns_same_engine_instance(self):
        first = session_module.get_engine()
        second = session_module.get_engine()
        assert first is second


class TestGetSessionFactory:
    def setup_method(self):
        _reset_module_state()

    def teardown_method(self):
        _reset_module_state()

    def test_returns_same_factory_instance(self):
        first = session_module.get_session_factory()
        second = session_module.get_session_factory()
        assert first is second


class TestGetDb:
    def setup_method(self):
        _reset_module_state()

    def teardown_method(self):
        _reset_module_state()

    def test_yields_a_session_and_closes_it_when_exhausted(self):
        fake_session = MagicMock()
        session_module._SessionLocal = MagicMock(return_value=fake_session)

        gen = session_module.get_db()
        db = next(gen)
        assert db is fake_session
        fake_session.close.assert_not_called()

        with pytest.raises(StopIteration):
            next(gen)
        fake_session.close.assert_called_once()

    def test_closes_session_even_if_caller_raises(self):
        fake_session = MagicMock()
        session_module._SessionLocal = MagicMock(return_value=fake_session)

        gen = session_module.get_db()
        next(gen)
        with pytest.raises(RuntimeError):
            gen.throw(RuntimeError("boom"))
        fake_session.close.assert_called_once()
