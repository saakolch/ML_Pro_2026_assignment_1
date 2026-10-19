"""Тесты схемы данных без датасета: маленькие DataFrame собираются прямо в тесте."""
import pandas as pd
import pandera.pandas as pa
import pytest

from grade_perform.data import EXPORT, ROWS


def _rows(n: int) -> list[dict]:
    """n заведомо валидных строк; Last и Overall различаются, чтобы не было дубликатов."""
    rows = []
    for i in range(n):
        rows.append(
            {
                "Department": "Business Administration",
                "Gender": "Male",
                "HSC": 4.17,
                "SSC": 4.84,
                "Income": "Low (Below 15,000)",
                "Hometown": "Village",
                "Computer": 3,
                "Preparation": "More than 3 Hours",
                "Gaming": "0-1 Hour",
                "Attendance": "80%-100%",
                "Job": "No",
                "English": 3,
                "Extra": "Yes",
                "Semester": "6th",
                "Last": round(3.0 + i * 0.1, 2),
                "Overall": round(3.1 + i * 0.1, 2),
            }
        )
    return rows


def test_good_rows_pass():
    ROWS.validate(pd.DataFrame(_rows(3)))


def test_corrupted_value_caught():
    bad = _rows(1)
    bad[0]["Last"] = 9.0  # контракт разрешает Last <= 4.0
    with pytest.raises(pa.errors.SchemaErrors) as err:
        ROWS.validate(pd.DataFrame(bad), lazy=True)
    assert "Last" in set(err.value.failure_cases["column"])


def test_small_dataset_rejected():
    # строки валидные и медиана в окне - выгрузку бракует именно объём
    with pytest.raises(pa.errors.SchemaErrors) as err:
        EXPORT.validate(pd.DataFrame(_rows(5)), lazy=True)
    checks = err.value.failure_cases["check"].astype(str)
    assert checks.str.contains("400").any()
    assert not checks.str.contains("медиана").any()
