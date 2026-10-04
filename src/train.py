import hashlib
import json
import os
from pathlib import Path

import mlflow
import mlflow.sklearn
import pandas as pd
import sklearn
from matplotlib.figure import Figure
from mlflow import MlflowClient
from mlflow.exceptions import MlflowException
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

DATA_PATH = Path(os.getenv("DATA_PATH", "artifact/ResearchInformation3.csv"))
MODEL_NAME = os.getenv("MODEL_NAME", "grade_perform")
EXPERIMENT = os.getenv("MLFLOW_EXPERIMENT", "grade_perform")
ALPHA = float(os.getenv("RIDGE_ALPHA", "1.0"))
MIN_GAIN = float(os.getenv("GATE_MIN_GAIN", "0.005"))
SEED = 42
SKOPS_TRUSTED = ["numpy.dtype", "sklearn.compose._column_transformer._RemainderColsList"]

NUMERIC = ["HSC", "SSC", "Computer", "English", "Last"]
CATEGORICAL = [
    "Department",
    "Gender",
    "Income",
    "Hometown",
    "Preparation",
    "Gaming",
    "Attendance",
    "Job",
    "Extra",
    "Semester",
]
TARGET = "Overall"


def load_and_validate(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    missing = set(NUMERIC + CATEGORICAL + [TARGET]) - set(df.columns)
    if missing:
        raise ValueError(f"missing columns: {sorted(missing)}")
    if len(df) < 400:
        raise ValueError(f"too few rows: {len(df)}")
    if not df[TARGET].between(1.0, 4.0).all():
        raise ValueError(f"target out of 1.0..4.0 range: {df[TARGET].min()}..{df[TARGET].max()}")
    return df


def build_pipeline(alpha: float) -> Pipeline:
    preprocess = ColumnTransformer(
        [
            (
                "num",
                Pipeline(
                    [("impute", SimpleImputer(strategy="mean")), ("scale", StandardScaler())]
                ),
                NUMERIC,
            ),
            (
                "cat",
                Pipeline(
                    [
                        ("impute", SimpleImputer(strategy="constant", missing_values="Missing")),
                        ("onehot", OneHotEncoder(drop="first", handle_unknown="ignore")),
                    ]
                ),
                CATEGORICAL,
            ),
        ]
    )
    return Pipeline([("preprocess", preprocess), ("model", Ridge(alpha=alpha))])


def champion_mae(client: MlflowClient) -> tuple[str | None, float | None]:
    try:
        mv = client.get_model_version_by_alias(MODEL_NAME, "champion")
    except MlflowException:
        return None, None
    return mv.version, client.get_run(mv.run_id).data.metrics.get("mae")


def main() -> dict:
    df = load_and_validate(DATA_PATH)
    features = NUMERIC + CATEGORICAL
    x_train, x_test, y_train, y_test = train_test_split(
        df[features], df[TARGET], test_size=0.2, random_state=SEED
    )

    pipeline = build_pipeline(ALPHA).fit(x_train, y_train)
    pred = pipeline.predict(x_test)
    mae = float(mean_absolute_error(y_test, pred))
    rmse = float(mean_squared_error(y_test, pred) ** 0.5)

    mlflow.set_experiment(EXPERIMENT)
    client = MlflowClient()
    old_version, old_mae = champion_mae(client)

    with mlflow.start_run() as run:
        fig = Figure(figsize=(5, 5))
        ax = fig.add_subplot()
        ax.scatter(y_test, pred, s=12)
        ax.plot([1.0, 4.0], [1.0, 4.0], "--")
        ax.set_xlabel("actual Overall")
        ax.set_ylabel("predicted Overall")
        mlflow.log_figure(fig, "pred_vs_actual.png")

        metadata = {
            "features": features,
            "target": TARGET,
            "bounds": [1.0, 4.0],
            "n_train": len(x_train),
            "data_rows": len(df),
            "sklearn": sklearn.__version__,
        }
        mlflow.log_params(
            {
                "alpha": ALPHA,
                "model": "Ridge",
                "seed": SEED,
                "data": str(DATA_PATH),
                "data_md5": hashlib.md5(DATA_PATH.read_bytes()).hexdigest(),
            }
        )
        mlflow.log_metrics({"mae": mae, "rmse": rmse})
        mlflow.log_dict(metadata, "metadata.json")
        info = mlflow.sklearn.log_model(
            pipeline,
            name="model",
            registered_model_name=MODEL_NAME,
            skops_trusted_types=SKOPS_TRUSTED,
        )
        version = info.registered_model_version

    promoted = old_mae is None or mae < old_mae - MIN_GAIN
    client.set_registered_model_alias(MODEL_NAME, "challenger", version)
    if promoted:
        client.set_registered_model_alias(MODEL_NAME, "champion", version)

    result = {
        "run_id": run.info.run_id,
        "version": version,
        "alpha": ALPHA,
        "mae": round(mae, 4),
        "rmse": round(rmse, 4),
        "champion_before": old_version,
        "champion_mae_before": None if old_mae is None else round(old_mae, 4),
        "promoted": promoted,
    }
    print(json.dumps(result, ensure_ascii=False))
    return result


if __name__ == "__main__":
    main()