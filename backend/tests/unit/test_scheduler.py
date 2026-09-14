"""Scheduler tests — APScheduler itself is mocked so nothing here
actually starts a background thread or waits on real intervals."""

from unittest.mock import MagicMock, patch

import app.scheduler as scheduler
from app.config import Settings
from app.ingestion.ingest_service import IngestResult


def setup_function(_fn):
    scheduler._scheduler = None


def teardown_function(_fn):
    scheduler._scheduler = None


class TestStartScheduler:
    def test_returns_none_and_starts_nothing_when_disabled(self):
        settings = Settings(_env_file=None, scheduled_ingest_enabled=False)
        with patch("app.scheduler.BackgroundScheduler") as mock_cls:
            result = scheduler.start_scheduler(settings)

        assert result is None
        mock_cls.assert_not_called()

    def test_registers_one_job_per_known_corpus_when_enabled(self):
        settings = Settings(
            _env_file=None, scheduled_ingest_enabled=True, scheduled_ingest_interval_hours=6
        )
        mock_instance = MagicMock()
        with (
            patch("app.scheduler.BackgroundScheduler", return_value=mock_instance),
            patch(
                "app.scheduler.list_available_corpora",
                return_value=["example-docs", "example-university"],
            ),
        ):
            result = scheduler.start_scheduler(settings)

        assert result is mock_instance
        assert mock_instance.add_job.call_count == 2
        job_ids = {call.kwargs["id"] for call in mock_instance.add_job.call_args_list}
        assert job_ids == {"ingest-example-docs", "ingest-example-university"}
        for call in mock_instance.add_job.call_args_list:
            assert call.args[1] == "interval"
            assert call.kwargs["hours"] == 6
        mock_instance.start.assert_called_once()

    def test_stores_the_running_scheduler_in_module_state(self):
        settings = Settings(_env_file=None, scheduled_ingest_enabled=True)
        mock_instance = MagicMock()
        with (
            patch("app.scheduler.BackgroundScheduler", return_value=mock_instance),
            patch("app.scheduler.list_available_corpora", return_value=["example-docs"]),
        ):
            scheduler.start_scheduler(settings)

        assert scheduler._scheduler is mock_instance


class TestStopScheduler:
    def test_shuts_down_and_clears_state_when_running(self):
        mock_instance = MagicMock()
        scheduler._scheduler = mock_instance

        scheduler.stop_scheduler()

        mock_instance.shutdown.assert_called_once_with(wait=False)
        assert scheduler._scheduler is None

    def test_is_a_noop_when_nothing_is_running(self):
        scheduler._scheduler = None
        scheduler.stop_scheduler()  # must not raise
        assert scheduler._scheduler is None


class TestRunScheduledIngest:
    def test_ingests_and_closes_the_session_on_success(self):
        fake_session = MagicMock()
        with (
            patch(
                "app.scheduler.get_session_factory", return_value=lambda: fake_session
            ),
            patch(
                "app.scheduler.ingest_corpus",
                return_value=IngestResult(sources_ingested=7, chunks_ingested=20),
            ) as mock_ingest,
        ):
            scheduler.run_scheduled_ingest("example-docs")

        mock_ingest.assert_called_once_with("example-docs", fake_session)
        fake_session.close.assert_called_once()

    def test_logs_and_still_closes_the_session_on_failure(self):
        fake_session = MagicMock()
        with (
            patch(
                "app.scheduler.get_session_factory", return_value=lambda: fake_session
            ),
            patch("app.scheduler.ingest_corpus", side_effect=RuntimeError("boom")),
        ):
            scheduler.run_scheduled_ingest("example-docs")  # must not raise

        fake_session.close.assert_called_once()
