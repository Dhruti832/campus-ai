"""/admin route tests — admin_service and the DB session are mocked;
DB behavior itself is covered by test_admin_service.py."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.db.session import get_db
from app.ingestion.ingest_service import IngestResult
from app.main import app

ADMIN_SETTINGS = Settings(_env_file=None, admin_api_key="secret-key")


@pytest.fixture
def client():
    app.dependency_overrides[get_db] = lambda: iter([MagicMock()])
    yield TestClient(app)
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture(autouse=True)
def _admin_key_configured():
    with patch("app.routes.admin.get_settings", return_value=ADMIN_SETTINGS):
        yield


class TestAdminAuth:
    def test_missing_key_is_rejected(self, client):
        response = client.get("/admin/corpora")
        assert response.status_code == 403

    def test_wrong_key_is_rejected(self, client):
        response = client.get("/admin/corpora", headers={"X-Admin-Key": "wrong"})
        assert response.status_code == 403

    def test_admin_disabled_when_no_key_configured(self, client):
        with patch(
            "app.routes.admin.get_settings",
            return_value=Settings(_env_file=None, admin_api_key=""),
        ):
            response = client.get("/admin/corpora", headers={"X-Admin-Key": ""})
        assert response.status_code == 403

    def test_correct_key_is_accepted(self, client):
        with patch("app.routes.admin.get_corpus_stats", return_value=[]):
            response = client.get("/admin/corpora", headers={"X-Admin-Key": "secret-key"})
        assert response.status_code == 200


class TestCorporaEndpoint:
    def test_returns_stats_from_service(self, client):
        fake_stats = [{"name": "example-docs", "sources": 7, "chunks": 20, "active": True}]
        with patch("app.routes.admin.get_corpus_stats", return_value=fake_stats):
            response = client.get("/admin/corpora", headers={"X-Admin-Key": "secret-key"})
        assert response.json() == fake_stats


class TestCreateCorpusEndpoint:
    def test_creates_a_corpus_and_returns_its_name(self, client):
        with (
            patch("app.routes.admin.list_available_corpora", return_value=["example-docs"]),
            patch("app.routes.admin.save_corpus_config") as mock_save,
        ):
            response = client.post(
                "/admin/corpora",
                json={"name": "acme-docs", "website_url": "https://docs.acme.com"},
                headers={"X-Admin-Key": "secret-key"},
            )
        assert response.status_code == 200
        assert response.json() == {"name": "acme-docs"}
        mock_save.assert_called_once()

    def test_rejects_a_name_that_already_exists(self, client):
        with patch("app.routes.admin.list_available_corpora", return_value=["acme-docs"]):
            response = client.post(
                "/admin/corpora",
                json={"name": "acme-docs", "website_url": "https://docs.acme.com"},
                headers={"X-Admin-Key": "secret-key"},
            )
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    def test_rejects_an_invalid_name(self, client):
        with patch("app.routes.admin.list_available_corpora", return_value=[]):
            response = client.post(
                "/admin/corpora",
                json={"name": "Not Valid!", "website_url": "https://docs.acme.com"},
                headers={"X-Admin-Key": "secret-key"},
            )
        assert response.status_code == 400

    def test_rejects_an_invalid_url(self, client):
        with patch("app.routes.admin.list_available_corpora", return_value=[]):
            response = client.post(
                "/admin/corpora",
                json={"name": "acme-docs", "website_url": "not-a-url"},
                headers={"X-Admin-Key": "secret-key"},
            )
        assert response.status_code == 400

    def test_requires_the_admin_key(self, client):
        response = client.post(
            "/admin/corpora",
            json={"name": "acme-docs", "website_url": "https://docs.acme.com"},
        )
        assert response.status_code == 403


class TestCorpusDetailEndpoint:
    def test_returns_the_config_for_a_dynamic_corpus(self, client):
        from app.config import CorpusConfig, CrawlConfig

        config = CorpusConfig(
            name="acme-docs",
            persona="You are Acme's bot.",
            crawl=CrawlConfig(seed_urls=["https://docs.acme.com"], max_pages=50),
        )
        with patch("app.routes.admin.load_dynamic_corpus_config", return_value=config):
            response = client.get(
                "/admin/corpora/acme-docs", headers={"X-Admin-Key": "secret-key"}
            )
        assert response.status_code == 200
        assert response.json() == {
            "name": "acme-docs",
            "website_url": "https://docs.acme.com",
            "persona": "You are Acme's bot.",
            "max_pages": 50,
        }

    def test_returns_404_for_an_unknown_or_built_in_corpus(self, client):
        with patch("app.routes.admin.load_dynamic_corpus_config", return_value=None):
            response = client.get(
                "/admin/corpora/example-docs", headers={"X-Admin-Key": "secret-key"}
            )
        assert response.status_code == 404

    def test_requires_the_admin_key(self, client):
        response = client.get("/admin/corpora/acme-docs")
        assert response.status_code == 403


class TestEditCorpusEndpoint:
    def test_updates_and_returns_the_name(self, client):
        from app.config import CorpusConfig

        with patch(
            "app.routes.admin.update_corpus_config",
            return_value=CorpusConfig(name="acme-docs", persona="Updated persona."),
        ) as mock_update:
            response = client.patch(
                "/admin/corpora/acme-docs",
                json={"persona": "Updated persona."},
                headers={"X-Admin-Key": "secret-key"},
            )
        assert response.status_code == 200
        assert response.json() == {"name": "acme-docs"}
        mock_update.assert_called_once()

    def test_returns_404_for_an_unknown_or_built_in_corpus(self, client):
        with patch("app.routes.admin.update_corpus_config", return_value=None):
            response = client.patch(
                "/admin/corpora/example-docs",
                json={"persona": "x"},
                headers={"X-Admin-Key": "secret-key"},
            )
        assert response.status_code == 404

    def test_rejects_an_invalid_website_url(self, client):
        with patch(
            "app.routes.admin.update_corpus_config",
            side_effect=ValueError("Not a valid website URL: 'not-a-url'"),
        ):
            response = client.patch(
                "/admin/corpora/acme-docs",
                json={"website_url": "not-a-url"},
                headers={"X-Admin-Key": "secret-key"},
            )
        assert response.status_code == 400

    def test_requires_the_admin_key(self, client):
        response = client.patch("/admin/corpora/acme-docs", json={"persona": "x"})
        assert response.status_code == 403


class TestRemoveCorpusEndpoint:
    def test_deletes_and_returns_confirmation(self, client):
        with patch("app.routes.admin.delete_corpus_config", return_value=True):
            response = client.delete(
                "/admin/corpora/acme-docs", headers={"X-Admin-Key": "secret-key"}
            )
        assert response.status_code == 200
        assert response.json() == {"deleted": "acme-docs"}

    def test_returns_404_for_an_unknown_or_built_in_corpus(self, client):
        with patch("app.routes.admin.delete_corpus_config", return_value=False):
            response = client.delete(
                "/admin/corpora/example-docs", headers={"X-Admin-Key": "secret-key"}
            )
        assert response.status_code == 404

    def test_requires_the_admin_key(self, client):
        response = client.delete("/admin/corpora/acme-docs")
        assert response.status_code == 403


class TestActiveCorpusEndpoint:
    def test_switches_corpus_and_returns_confirmation(self, client):
        with patch("app.routes.admin.set_active_corpus") as mock_set:
            response = client.post(
                "/admin/active-corpus",
                json={"corpus": "example-university"},
                headers={"X-Admin-Key": "secret-key"},
            )
        assert response.status_code == 200
        assert response.json() == {"active_corpus": "example-university"}
        mock_set.assert_called_once()

    def test_unknown_corpus_returns_400(self, client):
        with patch(
            "app.routes.admin.set_active_corpus", side_effect=ValueError("Unknown corpus: 'x'")
        ):
            response = client.post(
                "/admin/active-corpus",
                json={"corpus": "x"},
                headers={"X-Admin-Key": "secret-key"},
            )
        assert response.status_code == 400


class TestIngestEndpoint:
    def test_triggers_ingestion_and_returns_counts(self, client):
        with (
            patch("app.routes.admin.list_available_corpora", return_value=["example-docs"]),
            patch(
                "app.routes.admin.ingest_corpus",
                return_value=IngestResult(sources_ingested=7, chunks_ingested=20),
            ) as mock_ingest,
        ):
            response = client.post(
                "/admin/ingest",
                json={"corpus": "example-docs"},
                headers={"X-Admin-Key": "secret-key"},
            )
        assert response.status_code == 200
        assert response.json() == {"sources_ingested": 7, "chunks_ingested": 20}
        mock_ingest.assert_called_once()

    def test_unknown_corpus_returns_400(self, client):
        with patch("app.routes.admin.list_available_corpora", return_value=["example-docs"]):
            response = client.post(
                "/admin/ingest",
                json={"corpus": "does-not-exist"},
                headers={"X-Admin-Key": "secret-key"},
            )
        assert response.status_code == 400
