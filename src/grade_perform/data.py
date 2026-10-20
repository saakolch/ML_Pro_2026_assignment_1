"""Схема pandera на очищенный слой данных о студентах и шаг validate в MLflow.

  uv run python -m grade_perform.data      шаг validate: чистка, проверка, отчёт в MLflow; при нарушениях код выхода 1

Сырой слой datasets/ResearchInformation3.csv лежит в DVC и руками не правится.
Данные уже чистые: пропусков нет вовсе, полных дубликатов нет. Чистка сводится к
типам: баллы в float, счётные признаки в int. Значения не трогаем: варианты Income
с хвостовыми пробелами входят в словарь OneHot модели, их нормализация сломала бы
совместимость обучения и сервиса. Границы взяты из самих данных и их смысла.
"""
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

import pandas as pd
import pandera.pandas as pa

RAW_PATH = Path(os.getenv("DATA_PATH", "datasets/ResearchInformation3.csv"))
EXPERIMENT = os.getenv("MLFLOW_EXPERIMENT", "grade_perform")

# допустимые значения категорий - из самих данных (value_counts), не из головы
DEPARTMENTS = [
    "Business Administration",
    "Computer Science and Engineering",
    "Economics",
    "Electrical and Electronic Engineering",
    "English",
    "Journalism, Communication and Media Studies",
    "Law and Human Rights",
    "Political Science",
    "Public Health",
    "Sociology",
]
INCOME = [
    "High (Above 50,000)",
    "High (Above 50,000) ",
    "High (Above 50,000)  ",
    "Low (Below 15,000)",
    "Low (Below 15,000) ",
    "Lower middle (15,000-30,000)",
    "Lower middle (15,000-30,000) ",
    "Lower middle (15,000-30,000)  ",
    "Upper middle (30,000-50,000)",
    "Upper middle (30,000-50,000) ",
]
SEMESTERS = [
    "2nd", "3rd", "4th", "5th", "6th", "7th", "8th", "9th", "10th", "11th", "12th",
]

# правила для каждой строки: их можно проверить и на маленьком образце в CI.
# Идентификатора в данных нет, поэтому правила уникальности нет - вместо него
# на уровне выгрузки проверяем отсутствие полных дубликатов строк.
ROWS = pa.DataFrameSchema(
    {
        "Department": pa.Column(str, pa.Check.isin(DEPARTMENTS)),
        "Gender": pa.Column(str, pa.Check.isin(["Female", "Male"])),
        "HSC": pa.Column(float, pa.Check.in_range(2.17, 5.0)),  # аттестат, в данных от 2.17
        "SSC": pa.Column(float, pa.Check.in_range(3.0, 5.0)),  # школьный аттестат
        "Income": pa.Column(str, pa.Check.isin(INCOME)),
        "Hometown": pa.Column(str, pa.Check.isin(["Village", "City"])),
        "Computer": pa.Column(int, pa.Check.in_range(1, 5)),  # навык 1..5
        "Preparation": pa.Column(str, pa.Check.isin(["0-1 Hour", "2-3 Hours", "More than 3 Hours"])),
        "Gaming": pa.Column(str, pa.Check.isin(["0-1 Hour", "2-3 Hours", "More than 3 Hours"])),
        "Attendance": pa.Column(str, pa.Check.isin(["40%-59%", "60%-79%", "80%-100%"])),
        "Job": pa.Column(str, pa.Check.isin(["No", "Yes"])),
        "English": pa.Column(int, pa.Check.in_range(1, 5)),
        "Extra": pa.Column(str, pa.Check.isin(["No", "Yes"])),
        "Semester": pa.Column(str, pa.Check.isin(SEMESTERS)),
        "Last": pa.Column(float, pa.Check.in_range(1.0, 4.0)),  # GPA прошлых семестров
        "Overall": pa.Column(float, pa.Check.in_range(1.0, 4.0)),  # целевой GPA
    },
    strict=True,
)

# правила для выгрузки целиком: объём и распределение, на маленьком образце не проверить.
# Границы из данных: полная выгрузка 482 строк (порог 400 - минимум обучения из train.py),
# медиана Overall 3.29 (окно 3.0..3.6 ловит смену шкалы оценивания или когорты),
# пропусков нет вовсе (порог 5% на столбец ловит сломанную выгрузку),
# полных дубликатов нет (ловит повторно приклеенную выгрузку).
EXPORT = pa.DataFrameSchema(
    ROWS.columns,
    checks=[
        pa.Check(lambda df: len(df) >= 400, error="меньше 400 строк: выгрузка неполная"),
        pa.Check(
            lambda df: 3.0 <= df["Overall"].median() <= 3.6,
            error="медиана Overall вне 3.0..3.6: сменилась шкала оценивания или когорта",
        ),
        pa.Check(
            lambda df: df.isna().mean().max() < 0.05,
            error="доля пропусков больше 5% хотя бы в одном столбце",
        ),
        pa.Check(lambda df: df.duplicated().sum() == 0, error="есть полные дубликаты строк"),
    ],
    strict=True,
)


def file_md5(path: Path) -> str:
    """Тот же md5, что DVC пишет в .dvc-файл: по нему видно, на какой версии данных обучена модель."""
    return hashlib.md5(path.read_bytes()).hexdigest()


def load_raw(path: Path = RAW_PATH) -> pd.DataFrame:
    return pd.read_csv(path)


def clean(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()
    for col in ("HSC", "SSC", "Last", "Overall"):
        df[col] = df[col].astype("float64")
    for col in ("Computer", "English"):
        df[col] = df[col].astype("int64")
    return df.reset_index(drop=True)


def load_clean(path: Path = RAW_PATH) -> pd.DataFrame:
    return EXPORT.validate(clean(load_raw(path)), lazy=True)


def main() -> int:
    import mlflow

    raw = load_raw()
    df = clean(raw)
    md5 = file_md5(RAW_PATH)
    mlflow.set_experiment(EXPERIMENT)
    with mlflow.start_run(run_name="validate"):
        mlflow.log_params({"step": "validate", "data": str(RAW_PATH), "data_md5": md5})
        mlflow.log_metrics({"raw_rows": len(raw), "clean_rows": len(df)})
        try:
            EXPORT.validate(df, lazy=True)
        except pa.errors.SchemaErrors as e:
            fc = e.failure_cases
            summary = fc.groupby(["column", "check"], dropna=False).size().rename("cases").reset_index()
            with tempfile.TemporaryDirectory() as tmp:
                fc.head(1000).to_csv(Path(tmp) / "failure_cases.csv", index=False)
                mlflow.log_artifact(str(Path(tmp) / "failure_cases.csv"))
            mlflow.log_metric("failed_checks", len(summary))
            mlflow.set_tag("valid", "false")
            print("данные не прошли проверку, отчёт failure_cases.csv в MLflow:")
            print(summary.to_string(index=False))
            return 1
        mlflow.set_tag("valid", "true")
        mlflow.log_metrics(
            {
                "median_overall": float(df["Overall"].median()),
                "missing_share_max": float(df.isna().mean().max()),
                "duplicates": int(df.duplicated().sum()),
            }
        )
    result = {
        "valid": True,
        "data_md5": md5,
        "rows": len(df),
        "median_overall": round(float(df["Overall"].median()), 3),
        "duplicates": int(df.duplicated().sum()),
    }
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
