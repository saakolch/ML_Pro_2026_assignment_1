import psycopg
import pytest

from grade_perform.config import settings

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not settings.database_url,
        reason="needs Postgres: set DATABASE_URL",
    ),
]


@pytest.fixture()
def db_rows():
    request_ids = []
    yield request_ids
    if request_ids:
        with psycopg.connect(settings.database_url) as conn:
            for request_id in request_ids:
                conn.execute("DELETE FROM predictions WHERE request_id = %s", (request_id,))


def test_good_request_writes_row(client, good_row, db_rows):
    r = client.post("/v1/predict", json=good_row)
    assert r.status_code == 200
    body = r.json()
    db_rows.append(body["request_id"])

    with psycopg.connect(settings.database_url) as conn:
        row = conn.execute(
            "SELECT model_version, prediction, latency_ms, response_code, features "
            "FROM predictions WHERE request_id = %s",
            (body["request_id"],),
        ).fetchone()

    assert row is not None
    model_version, prediction, latency_ms, response_code, features = row
    assert model_version == body["model_version"]
    assert prediction == pytest.approx(body["prediction"])
    assert latency_ms >= 0
    assert response_code == 200
    assert features == good_row


def test_bad_request_writes_422_row(client, good_row, db_rows):
    bad_row = {k: v for k, v in good_row.items() if k != "Gender"}

    r = client.post("/v1/predict", json=bad_row)
    assert r.status_code == 422
    request_id = r.json()["request_id"]
    db_rows.append(request_id)

    with psycopg.connect(settings.database_url) as conn:
        row = conn.execute(
            "SELECT model_version, prediction, response_code, features "
            "FROM predictions WHERE request_id = %s",
            (request_id,),
        ).fetchone()

    assert row is not None
    model_version, prediction, response_code, features = row
    assert model_version == client.app.state.version
    assert response_code == 422
    assert prediction == -1.0
    assert features == bad_row
