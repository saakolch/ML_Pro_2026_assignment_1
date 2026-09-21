import psycopg
from psycopg.types.json import Json

from grade_perform.config import settings

DDL = """
CREATE TABLE IF NOT EXISTS predictions (

    request_id      uuid PRIMARY KEY,
    ts              timestamptz NOT NULL DEFAULT now(),
    model_version   text NOT NULL,
    features        jsonb NOT NULL,
    prediction      double precision NOT NULL,
    latency_ms      real,
    response_code   int NOT NULL

)
"""

def init():
    if not settings.database_url:
        return print("no url for db is provided")
    
    with psycopg.connect(settings.database_url) as conn:
        conn.execute(DDL)

def save_predictions(request_id, model_version, features, prediction, latency_ms, response_code):
    if not settings.database_url:
        return print("no url for db is provided")

    with psycopg.connect(settings.database_url) as conn:
        conn.execute(
            "INSERT INTO predictions (request_id, model_version, features, prediction, latency_ms, response_code) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (request_id, model_version, Json(features), prediction, latency_ms, response_code),
        )
