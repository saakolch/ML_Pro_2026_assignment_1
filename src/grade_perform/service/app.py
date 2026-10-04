import json
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

import joblib
import mlflow
import mlflow.sklearn
import pandas as pd
import psycopg
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from mlflow import MlflowClient
from pydantic import BaseModel

from grade_perform import db
from grade_perform.config import settings
from grade_perform.features import Features


class Prediction(BaseModel):
    model_config = {"protected_namespaces": ()}

    prediction: float
    model_version: str
    request_id: str
    latency_ms: float


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.model_name:
        try:
            mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
            client = MlflowClient()
            mv = client.get_model_version_by_alias(settings.model_name, settings.model_alias)
            app.state.pipeline = mlflow.sklearn.load_model(
                f"models:/{settings.model_name}@{settings.model_alias}"
            )
            meta_path = client.download_artifacts(mv.run_id, "metadata.json")
            app.state.meta = json.loads(Path(meta_path).read_text(encoding="utf-8"))
            app.state.version = f"registry-v{mv.version}"

        except Exception as e:  # noqa: BLE001
            print(f"registry load failed, error: {e}")

    else:
        try:
            bundle = joblib.load(settings.model_path) #btw why setting has a link but not a package - so will it break docker?
            app.state.pipeline = bundle["pipeline"]
            app.state.meta = bundle["metadata"]
            app.state.version = str(bundle["metadata"].get("version"))

        except Exception as e: # noqa: BLE001
            print(f"there is no model, error: {e}")
            #app.state.pipeline = None @check if comment will breal anything

    db.init() 

    yield

app = FastAPI(lifespan=lifespan)

@app.get("/health")
def health_check():
    return {"status": "ok", "model_version": getattr(app.state, "version", "not provided")}

@app.get("/ready")
def ready_check():
    if not getattr(app.state, "pipeline", None):
        raise HTTPException(status_code=503, detail="no model is loaded")

    return {"status": "is_ready"}

@app.post("/v1/predict")
def predict(features: Features, bg: BackgroundTasks) -> Prediction:
    t0 = time.perf_counter()
    request_id = str(uuid.uuid4())
    latency_ms = 0.0
    features_clear = features.model_dump()

    df = pd.DataFrame([features_clear]).reindex(columns=app.state.meta["features"])
    
    overall = float(app.state.pipeline.predict(df)[0])

    latency_ms = round((time.perf_counter() - t0) * 1000, 2)

    bg.add_task(db.save_predictions, request_id, app.state.version, features_clear, overall, latency_ms, 200)

    
    return Prediction(prediction=overall, model_version=app.state.version, request_id=request_id, latency_ms=latency_ms)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, err: RequestValidationError):
    t0 = time.perf_counter()
    request_id = str(uuid.uuid4())

    try:
        raw_body = await request.json()

    except ValueError:
        raw_body = {"error": "Invalid json input"}

    error_details = str(err.errors())
    latency_ms = round((time.perf_counter() - t0) * 1000, 2)

    try:
        db.save_predictions(request_id=request_id, model_version=app.state.version, features=raw_body, prediction=-1.0, latency_ms=latency_ms, response_code=422)
    except psycopg.Error as db_err:
        print(f"Failed logging 422 to DB: {db_err}")

    return JSONResponse(status_code=422, content={"details": error_details, "request_id": request_id})


