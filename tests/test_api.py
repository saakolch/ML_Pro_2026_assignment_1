def test_ready(client):
    assert client.get("/ready").status_code == 200

def test_health(client, good_row):
    r = client.get("/health")
    assert r.status_code == 200
    assert "model_version" in r.json()
    
def test_predict_no_gender(client, good_row):
    payload = {k: v for k, v in good_row.items() if k != "Gender"}
    r = client.post("/v1/predict", json=payload)
    assert r.status_code == 422


def test_predict_bad_gender(client, good_row):
    r = client.post("/v1/predict", json = {**good_row, "Gender": "they"})
    assert r.status_code == 422

def test_predict_empty_body(client):
    assert client.post("/v1/predict", json={}).status_code == 422

def test_predict_extra_field_forbidden(client, good_row):
    r = client.post("/v1/predict", json={**good_row, "Hacker": True})
    assert r.status_code == 422

def test_predict_garbage_types(client, good_row):
    r = client.post("/v1/predict", json={**good_row, "HSC": "banana", "Computer": "three"})
    assert r.status_code == 422
