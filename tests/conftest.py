import pytest
from fastapi.testclient import TestClient

from grade_perform.service.app import app


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as client:
        yield client

@pytest.fixture()
def good_row():
    return {
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
        "Last": 3.22,
    }
