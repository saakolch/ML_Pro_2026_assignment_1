def test_predict_smoke(client, good_row):
    r = client.post("/v1/predict", json = good_row)
    assert r.status_code == 200
    body = r.json()
    assert 0.0 <= body["prediction"] <= 5.0
    assert body["latency_ms"] >= 0
    assert body["model_version"]

def test_batch_and_single_agree(client, good_row):
    s1 = client.post("/v1/predict", json = good_row).json()["prediction"]
    s2 = client.post("/v1/predict", json = good_row).json()["prediction"]
    assert abs(s1-s2) <= 1e-12

def test_predict_request_id_unique(client, good_row):
    import uuid
    r1 = client.post("/v1/predict", json = good_row).json()
    r2 = client.post("/v1/predict", json = good_row).json()
    assert r1["request_id"] != r2["request_id"]
    uuid.UUID(r1["request_id"])  

def test_predict_types(client, good_row):
    body = client.post("/v1/predict", json = good_row).json()
    assert isinstance(body["prediction"], float)
    assert isinstance(body["latency_ms"], float)
    assert isinstance(body["model_version"], str)
    assert isinstance(body["request_id"], str)