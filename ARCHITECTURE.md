# ARCHITECTURE — grade_perform

A FastAPI service that predicts a student's GPA (`Overall`, 1.0–4.0) with Ridge regression, plus the machinery around it: tests, container, Kubernetes, CI/CD, a model registry with a promotion gate, and versioned data. This document describes the system **as it is** in this repo — each component paired with the reason it exists.

---

## 1. The system in one picture

```mermaid
flowchart LR
    subgraph MACHINE["Your machine"]
        subgraph K["kind cluster (Docker)"]
            TR["Traefik ingress"] --> SVC["Service :8000"]
            SVC --> P1["Pod api (replica 1)"]
            SVC --> P2["Pod api (replica 2)"]
            P1 --> PG[("Postgres<br>predictions table")]
            P2 --> PG
            P1 -.->|"startup: load model@champion"| MLF["MLflow registry<br>mlflow.localhost :5000"]
            P2 -.-> MLF
            RUN["GitHub runner container<br>(self-hosted, kind)"] -->|"docker save + kubectl apply"| K
        end
        DVC[("../dvc-storage<br>raw CSV")]
        TRN["train.py<br>(manual launch)"]
        DVC -->|"dvc checkout"| TRN
        TRN -->|"register version + gate"| MLF
        GHA["GitHub Actions cloud<br>tests + build"] -->|"only on main"| RUN
    end

    GIT["git<br>code + .csv.dvc pointer"] -.-> GHA
    GIT -.->|"dvc pointer"| DVC

    U["Client<br>(curl / browser / locust)"] -->|"grade-perform.localhost:80"| TR
```

Three separate flows, one per line of the diagram:

| Flow | Path | Frequency |
|---|---|---|
| **Request flow** | client → Traefik → Service → pod → predict → Postgres row | every prediction |
| **Model flow** | train.py → MLflow (challenger always, champion if gate passes) → pod restart → pod fetches champion | every training run |
| **Code flow** | git push → Actions: tests + build (cloud) → deploy job on runner (your machine) → new image in kind | every merge to main |

---

## 2. The cast — what each piece is, and why it exists

| Component | What it is here | Why it exists (the reason) |
|---|---|---|
| `artifact/train.ipynb` | The original notebook that trained the first model | The origin of everything; the service was born from its output |
| `artifact/ridge_model.joblib` | Serialized sklearn `Pipeline` (preprocessing + Ridge) + metadata dict | Lets the service run **without** MLflow — for compose, CI tests, and as a fallback |
| `artifact/ResearchInformation3.csv` + `.csv.dvc` | The dataset (66 KB); only the small `.dvc` **pointer** (md5 + size) is in git | Git stores code, not raw data; DVC stores data and lets any version be restored byte-for-byte |
| `src/grade_perform/features.py` | Pydantic contract: 15 fields, exact names, types, ranges, `extra='forbid'` | The model is a function over *specific* features — garbage must be rejected at the door, before touching the model |
| `src/grade_perform/config.py` | Settings read from env vars / `.env` | Same code, different environments: local uses defaults, cluster gets settings injected by ConfigMap |
| `src/grade_perform/service/app.py` | The API: `lifespan` loads the model, `/health`, `/ready`, `/v1/predict`, a 422 logger | Turns a model file into a product: always-on, checkable, observable |
| `src/grade_perform/db.py` | `init()` (create table) + `save_predictions()` (insert row) | Every request becomes data — the raw material for future retraining and drift analysis |
| `src/train.py` | Trains Ridge, logs params/metrics/artifacts to MLflow, applies the **gate** | New model versions must be produced and *filtered* by a rule, not by a human's vibe |
| `tests/` | Contract tests (422s), smoke tests (sane output), integration tests (real Postgres) | CI must be able to prove the service works **without** a cluster, a registry, or the dataset |
| `Dockerfile` | uv-based image; deps layer before code layer; `COPY artifact/` | Kills "works on my machine"; layer order makes rebuilds take seconds, not minutes |
| `compose.yaml` | api + Postgres locally, with healthcheck + depends_on | One command to check the whole local story: predict lands in a real DB |
| `k8s/` (6 manifests) | Deployment (2 replicas, 3 probes, resources), Service, Ingress, ConfigMap, Postgres, HPA | Kubernetes decides if a pod lives or dies (probes), what settings it gets (ConfigMap), and when to scale (HPA) |
| `platform/` | kind config, MLflow manifests, Traefik, metrics-server values | The **platform** your app stands on — shared infra, not your code; all pieces your service *depends on* |
| `.github/workflows/ci.yml` | 3 jobs: tests → build → deploy (+ diagnosis) | Every push must prove itself automatically; delivery to the cluster must be one green run away |
| `locustfile.py` | Load generator: 9× predict, 1× health | A service is also a performance claim — this is how you measure it and drive the HPA |
| DVC (`.dvc/`, `.csv.dvc`) | Data versioning with a local storage folder | Model version ↔ data version must be linkable: `data_md5` is logged into every MLflow run |

**The one detail that explains half the repo — the two model-loading modes** (`app.py → lifespan()`):

- `MODEL_NAME` is set (cluster: ConfigMap) → load `grade_perform@champion` from the MLflow registry over the network. The model arrives at **pod startup**, not at image build — that's why swapping the alias changes the served model without any rebuild.
- `MODEL_NAME` is empty (local, CI) → load `artifact/ridge_model.joblib` from disk. That's why `Dockerfile` does `COPY artifact/` — the image ships a fallback model.

---

## 3. Follow one request

`POST /v1/predict` with a JSON body:

1. `grade-perform.localhost` resolves to 127.0.0.1 → port 80 → kind's `extraPortMappings` → 30080 in the node → Traefik.
2. Traefik reads the `Ingress` rule (`k8s/ingress.yaml`: host `grade-perform.localhost`) → forwards to Service `grade-perform-api:8000` → one of the pods.
3. FastAPI matches the route (`app.py → predict()`); the body is validated by `Features` (`features.py`) **before any of your code runs**. Anything wrong → 422 → the `validation_exception_handler` logs a row with `response_code=422` and still returns a `request_id`.
4. Valid body → `features.model_dump()` → one-row DataFrame → `pipeline.predict()` → float.
5. Response: `{prediction, model_version, request_id, latency_ms}`.
6. After the response is sent, a **background task** writes the row to Postgres (`db.py → save_predictions`) — including the model version, so the log knows *which* model produced it.

---

## 4. Follow one model version

`uv run python src/train.py` (with MLflow reachable, e.g. through `mlflow.localhost`):

1. Load CSV, sanity-check it (`load_and_validate`): required columns, ≥400 rows, target in 1.0–4.0.
2. Split 80/20, build `Pipeline(OneHot + Imputer + StandardScaler → Ridge(alpha))`, fit, compute MAE/RMSE.
3. Open an MLflow run: log `alpha`, `data_md5` (hash of the exact CSV bytes), a pred-vs-actual figure, `metadata.json`, and register the model → **new version N**.
4. **The gate** (`train.py → main()`): fetch the current `champion` and its MAE. New version always gets alias `challenger`. It takes `champion` only if `mae < old_mae − MIN_GAIN` (0.005) — or if no champion exists yet.
5. The running pods know nothing about this. The swap happens when you restart them: `kubectl rollout restart deploy/grade-perform-api` → new pods start → `lifespan` asks the registry for `grade_perform@champion` → gets whichever version the alias points to *right now*. Same image, possibly different model.

Rollback = re-point `champion` in the MLflow UI + restart. No rebuild, no new code.

---

## 5. Follow one git push

`git push` to `main` triggers `.github/workflows/ci.yml`:

1. **tests** (GitHub cloud): real Postgres as a service container; `ruff check`, then pytest. Integration tests run because `DATABASE_URL` is set; contract/smoke tests don't need MLflow (joblib mode).
2. **build** (cloud, `main` only, after tests): build image, push to GHCR tagged `sha-<commit>` — the image is identified by code version, not by a mutable `latest`.
3. **deploy** (self-hosted runner, `main` only): this job physically *cannot* run in GitHub's cloud — the kind cluster lives inside Docker on your machine, behind NAT, invisible from outside. So a runner container sits *inside the kind Docker network* and:
   - builds the image locally, injects it into kind via `docker save | ctr images import`;
   - renders the DB secret from GitHub Secrets with `--dry-run=client -o yaml | kubectl apply` (idempotent — safe on re-deploy);
   - applies `k8s/`, waits for `rollout status`;
   - **smoke test** through the Ingress: `/health` must show `registry-v…` (model really came from the registry), the prediction must be sane, and the DB must contain the row with exactly that `request_id`;
   - on any failure, a `diagnosis` step (`if: failure()`) prints pod states and logs.

A pull request runs **only** the `tests` job — broken code never builds an image or touches the cluster.

---

## 6. Where everything lives

| Thing | Where | How to find the right version |
|---|---|---|
| Code, manifests, CI | git (GitHub) | commit sha; image tags embed it |
| Dataset CSV | `../dvc-storage` (local folder; HW4 → S3 in cluster) | git holds the `.csv.dvc` pointer with md5 |
| Trained model | MLflow registry (inside cluster, sqlite + PVC) | aliases `champion` / `challenger` on `grade_perform`; each version's run has `data_md5` |
| Fallback model | `artifact/ridge_model.joblib` — in git **and** baked into the image | the notebook that produced it is next to it |
| Container image | GHCR (`sha-…` tag) + loaded into kind by the deploy job | tag = commit sha |
| Request logs | Postgres, `predictions` table (cluster) | query by `request_id` |
| DB password | GitHub Secrets → K8s Secret `app-db-credentials` | never in git, never in ConfigMap |

---

## 7. Self-check: interview-style questions

Not fact checks — each question is a chain. To *arrive* at the answer you must understand a sequence of elements; the hidden block only tells you where to verify yourself.

### Q1. A request with `"Gender": "they"` got a 422 with a `request_id` in the body. Who exactly rejected it, at what moment, and why is that check there and not inside the predict function?

Build the answer through these elements:
1. The HTTP request reaches FastAPI — which layer looks at the body first, your code or something else?
2. What does Pydantic do with `Gender: Literal["Male", "Female"]` and `extra='forbid'`?
3. Where does execution stop when validation fails — does `predict()` ever start?
4. Which function still runs, and what does it write to Postgres?
5. Why fail at the door instead of deep inside the app?

<details><summary>Self-check — where to verify</summary>

`features.py` (the contract), `app.py → predict()` signature (validation is implicit in the type hint), `app.py → validation_exception_handler` (the 422 row). Reason: the model must never see garbage — the contract is the boundary of your system.
</details>

### Q2. You re-pointed `champion` to version 1 in the MLflow UI, ran `kubectl rollout restart`, and `/health` changed from `registry-v3` to `registry-v1`. The image was never rebuilt. How is that possible?

Elements:
1. What does the pod *contain* vs what does it *fetch* at startup?
2. When does `lifespan` resolve `grade_perform@champion` — build time, deploy time, or pod start time?
3. What does `rollout restart` actually change (hint: nothing in the image)?
4. Why did the course choose an **alias** (`champion`) instead of pinning a version number in ConfigMap?

<details><summary>Self-check — where to verify</summary>

`k8s/configmap.yaml` (MODEL_NAME + MODEL_ALIAS, no version number), `app.py → lifespan()` (registry branch), MLflow registry UI (Aliases column). Reason: alias = a stable name that means "the current best", so rollback is a metadata edit, not a deployment.
</details>

### Q3. Someone deploys this service into a fresh cluster where no model was ever trained. Walk through what happens, in order, and say which exact probe fails.

Elements:
1. Pod starts, `lifespan` calls `get_model_version_by_alias` — what does MLflow return?
2. The exception is caught and *printed* — does the pod crash?
3. Is `app.state.pipeline` set? What does `/ready` return, and `/health`?
4. Which Kubernetes probe hits `/ready`, and what does a pod look like in `kubectl get pods` when it fails?
5. What does the CI `deploy` job do while this is going on (think `kubectl rollout status`)?

<details><summary>Self-check — where to verify</summary>

`app.py → lifespan()` (the `except` branch), `/ready` (503 when no pipeline), `k8s/deployment.yaml` (readinessProbe), REPORT_2 answer to question 5 — you already described this exact scenario. Reason: readiness separates "process alive" from "actually able to serve" — liveness alone would keep a useless pod alive forever.
</details>

### Q4. Name every hop of the DB password: from the GitHub settings page to the environment variable inside the container. Why would configmap.yaml be the wrong place for it?

Elements:
1. Where the value is stored in GitHub and how the workflow receives it (`secrets.DB_PASSWORD`).
2. Why the workflow renders a manifest with `--dry-run=client -o yaml` instead of `kubectl create secret`.
3. What object now exists in the cluster, and who references it (`secretKeyRef` in which file?).
4. Who injects it into the container process.
5. What is the difference between a ConfigMap and a Secret in terms of *where the bytes live* (git vs cluster) and visibility.

<details><summary>Self-check — where to verify</summary>

`ci.yml → deploy → taking secrets`, `k8s/deployment.yaml → env: DATABASE_URL → secretKeyRef`, `k8s/postgres.yaml` (same secret). Reason: the repo is public — anything committed is public; Secrets live in the cluster only, rendered at deploy time.
</details>

### Q5. Why do `tests` and `build` run in GitHub's cloud while `deploy` cannot? What property of your cluster forces a self-hosted runner, and what exactly does the runner need access to?

Elements:
1. Where does the kind cluster physically run (which process, whose network)?
2. Can a GitHub cloud runner reach `127.0.0.1:80` of your machine? Why not (one word: NAT)?
3. Why does the runner run with `--network kind` — what does it need to reach inside the cluster?
4. Why does it need the Docker socket — what two operations does it perform with Docker?
5. What would you have to expose publicly to avoid the runner, and why is that worse?

<details><summary>Self-check — where to verify</summary>

`ci.yml → deploy: runs-on: [self-hosted, kind]`, REPORT_2 answers 1–2 (you wrote this reasoning yourself). Reason: the cluster is private; the runner is the bridge that lives *inside* the same Docker network.
</details>

### Q6. The smoke test greps `/health` for the string `registry-v` instead of just checking HTTP 200. What failure does that catch that a plain 200 would not?

Elements:
1. What are the two possible model sources, and which one does `/health` show in each?
2. If the registry fetch fails, does `/health` still return 200? (Read the `except` branch.)
3. So what does `registry-v` prove that `status: ok` does not?
4. HW3 required three smoke assertions — which three, and what does each prove?

<details><summary>Self-check — where to verify</summary>

`ci.yml → smoke` (all three assertions), `app.py → /health` vs `/ready`. Reason: a service can be "up" while serving the wrong thing; the smoke test verifies the *wiring* (registry → pod), not just liveness.
</details>

### Q7. Two replicas start simultaneously against an empty database; both call `db.init()`. What does `init()` do, and what race could exist here? The seminar's reference code wrapped this in `pg_advisory_xact_lock` — what would that add?

Elements:
1. What single statement does `init()` run, and what does `IF NOT EXISTS` make it?
2. Can two simultaneous `CREATE TABLE IF NOT EXISTS` statements still conflict at the catalog level?
3. What does an advisory lock do to two racing transactions?
4. Who else must already exist before the pods start, and what happens to a request if the table doesn't exist yet?

<details><summary>Self-check — where to verify</summary>

`db.py → init()` (no lock in your version — that's the honest as-it-is state), REPORT_1 answer to question 6 (your own explanation of the seminar version). Reason: replicas are independent processes; schema creation is a shared, race-prone operation.
</details>

### Q8. `git clone` a fresh copy: there is no CSV anywhere, yet tests pass and the image builds. Explain where the data actually lives, and why neither the tests nor the running service need it.

Elements:
1. What is in git — the data, or a pointer? What does the pointer contain?
2. Which single component is the CSV's only consumer in the whole repo?
3. What do CI tests use instead of the dataset (`good_row`)?
4. How does `data_md5` in an MLflow run let you restore *exactly* the data that trained version N?
5. Order of operations: what must happen first — `git push` or `dvc push` — and what breaks otherwise?

<details><summary>Self-check — where to verify</summary>

`artifact/ResearchInformation3.csv.dvc`, `.dvc/config` (remote = local folder), `train.py` (`data_md5` param), `tests/conftest.py` (fixtures). Reason: git and DVC store different things; the service consumes models, not datasets — only training does.
</details>

### Q9. The HPA shows `<unknown>` targets for the first two minutes, and it *cannot work at all* without `requests.cpu` in the Deployment. Why does autoscaling depend on that line?

Elements:
1. What does HPA compute (the formula: replicas × current load ÷ target)?
2. Utilization is a **percentage of what** — limits or requests?
3. No requests → what happens to the denominator?
4. Where do CPU numbers come from (which component, which file configures it, which flag in kind)?

<details><summary>Self-check — where to verify</summary>

`k8s/hpa.yaml`, `k8s/deployment.yaml → resources.requests`, `platform/metrics-server-values.yaml` (`--kubelet-insecure-tls`). Reason: HPA scales on relative load; without a baseline (`requests`) a percentage is undefined.
</details>

### Q10. The DB write happens in `BackgroundTasks`, after the response is already sent. What problem does that solve, and what new risk does it introduce?

Elements:
1. Compare: time of a predict call vs time of a Postgres insert — who should wait for whom?
2. When exactly does the background task run (after response? before?).
3. If the DB is down, what does the client experience — error, or a prediction with a lost log row?
4. Why is it acceptable for *logging* to be best-effort but not for *predicting*?

<details><summary>Self-check — where to verify</summary>

`app.py → predict()` (`bg.add_task`), `db.py → save_predictions` (silent skip without DATABASE_URL). Reason: serving traffic is the primary job; logging is secondary and must never add latency or fail requests.
</details>

---

*Written from the repo as of now (HW1–3 done, HW4 not started). Line numbers may drift as you edit — component and function names are the stable anchors.*
