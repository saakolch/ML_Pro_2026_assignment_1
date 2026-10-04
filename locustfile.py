from locust import HttpUser, between, task

PAYLOAD = {
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


class ApiUser(HttpUser):
    wait_time = between(0, 0.2)

    @task(9)
    def predict(self):
        self.client.post("/v1/predict", json=PAYLOAD)

    @task(1)
    def health(self):
        self.client.get("/health")