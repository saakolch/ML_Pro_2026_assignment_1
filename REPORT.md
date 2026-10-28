# REPORT — итоговый проект (все домашки)

Репозиторий: https://github.com/saakolch/ML_Pro_2026_assignment_1 (ветка main)

## ДЗ-1 (семинар 1): сервис, тесты, docker, k8s

| Пункт задания | Доказательство |
|---|---|
| 1. Артефакт с паспортом (joblib: pipeline + metadata) | `artifact/ridge_model.joblib` + ноутбук обучения `artifact/train.ipynb`; metadata: версия, список фичей (`NUMERIC+CATEGORICAL`), bounds 1.0–4.0 — грузится в `app.py:60-64` |
| 2. Проект на uv (src-layout) | `src/grade_perform/`, `pyproject.toml`, `uv.lock`, `.python-version`; `uv sync && uv run python -c "import grade_perform"` |
| 3. FastAPI-сервис (4 точки, lifespan, 422) | `src/grade_perform/service/app.py` — `/health`, `/ready`, `/v1/predict`, автодоки `/docs`; ответ: prediction, model_version, request_id, latency_ms |
| 4. Логи в Postgres (+ поле response_code) | `src/grade_perform/db.py` — таблица `predictions` с `response_code`; без DATABASE_URL сервис работает и не логирует (db.py:21-22) |
| 5. Тесты (≥6: контракт 422, smoke, детерминизм) | `tests/` — 17 passed; контракт: test_predict_types + 422-handler в app.py:109; детерминизм: test_batch_and_single_agree |
| 6. Docker и compose | `Dockerfile` (uv, слой зависимостей до кода, --frozen --no-dev), `compose.yaml` (db healthcheck, api depends_on condition) |
| 7. Kubernetes (2 реплики, 3 пробы, port-forward) | `k8s/deployment.yaml` (replicas 2, startup/liveness/readiness), `k8s/service.yaml` |
| 8. README (3 команды + 4 скрина) | `README.md` — pytest, compose, kind + скрины (images/image.png … image-9.png) |

## ДЗ-2 (семинар 2): CI/CD

| Пункт задания | Доказательство |
|---|---|
| 1. Пайплайн tests/build/deploy | Полный прогон: https://github.com/saakolch/ML_Pro_2026_assignment_1/actions/runs/36322402594 |
| 1а. Пакет в GHCR, тег по sha | https://github.com/saakolch/ML_Pro_2026_assignment_1/pkgs/container/ml_pro_2026_assignment_1 |
| 2. PR с красным → зелёным | https://github.com/saakolch/ML_Pro_2026_assignment_1/pull/1 |
| 3а. Конфиг (путь к модели) | Прогон с проверкой пути из ConfigMap; сломанный тест: https://github.com/saakolch/ML_Pro_2026_assignment_1/actions/runs/36326046542 → зелёный: /actions/runs/36326320274 |
| 3б. Секрет (имя secretRef) | красный: /actions/runs/36326492154 → зелёный: /actions/runs/36326546543 |
| 3в. Ресурсы (1000000000Mi) | красный: /actions/runs/36326492154 → зелёный: /actions/runs/36326546543 |

## ДЗ-3 (семинар 3): платформа, реестр, DVC, HPA

| Пункт задания | Доказательство |
|---|---|
| 1. Платформа: kind:80, MLflow, Traefik, Ingress | REPORT_2 image.png (pods+ingress), image-1.png (MLflow на mlflow.localhost) |
| 2. Реестр и гейт (MAE, MIN_GAIN=0.005) | REPORT_2: v1 α=1.0 mae 0.1629 promoted=true; v2 α=100 mae 0.1838 promoted=false; v3 α=10 mae 0.1532 promoted=true; обоснование MIN_GAIN — image-3.png; артефакт pred_vs_actual.png (log_figure) |
| 3. Сервис по алиасу + откат без пересборки | REPORT_2 image-4.png: /health registry-v3 → registry-v1 за 51 сек |
| 4. CI/CD в свой кластер (runner) | https://github.com/saakolch/ML_Pro_2026_assignment_1/actions/runs/37215423658 (image-8, image-9) |
| 5. DVC (локальный remote, две версии данных) | image-6.png, image-7.png; data_md5 в params каждого прогона train.py:129 |
| 6. HPA (2→6 реплик, locust через Ingress) | image-10.png, image-11.png, image-12.png; requests.memory 512Mi→320Mi по замеру (коммит 24b595c) |
| 7. Три красных прогона с диагнозом | REPORT_2, раздел «Ошибки» + описание в ответах (config path / KIND_CLUSTER / Ingress host) |

## ДЗ-4 (итоговый проект)

| Пункт задания | Доказательство |
|---|---|
| 1. Платформа одной командой (up.sh) | `platform/` (up.sh, kind-config, traefik/mlflow/s3/airflow/ingress), image-13.png |
| 2. Метрики и дашборд | `app.py:25-28` (бакеты из замера p50=13.5мс, grade_perform_model_info, grade_perform_prediction), `k8s/monitoring/servicemonitor.yaml` + `dashboard.yaml` (grafana_dashboard: "1"), `scripts/traffic.py`, preStop в deployment.yaml; дашборд под трафиком — image-14.png |
| 3. DVC+S3 в кластере | `.dvc/config` (laptop+cluster → s3://dvc), указатель `datasets/ResearchInformation3.csv.dvc` в репо, `.dvc` папка: https://github.com/saakolch/ML_Pro_2026_assignment_1/tree/main/.dvc, бакет — image-15.png, Dockerfile: COPY .dvc/config + datasets/*.dvc + core.no_scm |
| 4. Проверка данных (pandera, valid=false) | `src/grade_perform/data.py` (ROWS+EXPORT), тесты без датасета `tests/test_data.py` (3 шт), зелёный CI: https://github.com/saakolch/ML_Pro_2026_assignment_1/actions/runs/39270604387, MLflow validate valid=false + failure_cases.csv — image-15.png |
| 5. Конвейер в Airflow (3 сценария) | `dags/grade_perform_retrain.py` (KubernetesPodOperator + dvc pull -r cluster + short_circuit + rollout); кейс 1 — image-17.png (все зелёные, rollout выполнен); кейс 2 — image-18.png (rollout skipped, только @challenger); кейс 3 — image-16.png (validate красный) + откат image-19.png (git revert b9ca85c, dvc checkout, reran); Model registry с aliases — image-20.png |
| 6. CI/CD целиком (deploy на runner) | `deploy` на `[self-hosted, kind]`: https://github.com/saakolch/ML_Pro_2026_assignment_1/actions/runs/39361233422 |

## Переделки (по фидбеку)

| Пункт фидбека | Что сделано | Ссылка |
|---|---|---|
| «Базовой части нет: platform/up.sh, Airflow, S3, метрики, ServiceMonitor, дашборд, preStop, pandera, dags» | Всё реализовано и лежит в main; ревью делалось по устаревшему состоянию remote | main: platform/, dags/, src/grade_perform/data.py, k8s/monitoring/ — коммиты 83aa388…d1add83 |
| «DVC смотрит в ../../dvc-storage, Dockerfile не копирует .dvc» | `.dvc/config` → laptop+cluster на s3://dvc (RustFS в кластере); Dockerfile: COPY .dvc/config + datasets/*.dvc + core.no_scm; в .dockerignore .dvc/cache, tmp, config.local | коммит с Task 3 (см. git log) |
| «README quickstart» | Переписан README: git clone → up.sh → данные в S3 → первый champion → runner → deploy → ответ через Ingress | |
| «REPORT.md в корне с таблицей» | Этот файл: таблица «пункт → доказательство» + «Переделки» | текущий коммит |
| «ConfigMap не подключён к поду, MODEL_PATH не доходит, model_path нет в /health» | Исправлено: envFrom configMapRef grade-perform-config в deployment.yaml; model_path добавлен в ответ /health | deployment.yaml:28-30, app.py /health (этот коммит) |
| «pg_advisory_xact_lock нет в db.init()» | Исправлено: advisory lock в транзакции вокруг CREATE TABLE — при 2 репликах и пустой базе инициализация последовательна | db.py init() (этот коммит) |
| «Smoke не проверяет смысл ответа» | Исправлено: в smoke добавлен assert, что prediction в диапазоне Overall | ci.yml, шаг smoke |
| «Поломки 2/3 сделаны в Postgres, а не в сервисе» | Переделываются против deployment.yaml (несуществующий secretRef + requests.memory 128000000Mi у API): красный → починка → зелёный ||
| «Ответы на вопросы неверные (время build, ImagePullBackOff, статусы, settings.png)» | Исправлено: REPORT_1 ответ 1 — время job build 13/19 с (холодная 47 с, прогон 36314772071); ответ 2 — ImagePullBackOff = старый ReplicaSet с grade-perform:hw1 до set image, kubectl apply не ждёт поды (про rollout status); ответ 7 — что видно по логам на каждом типе поломки | REPORT_1.md, Вопросы 1–2 и 7 (переписаны) |
| «ДЗ3 одним коммитом без PR, красные прогоны ruff, hpa.yaml создан руками» | hpa.yaml теперь применяется через CI (kubectl apply -f k8s/ вместе с остальными манифестами); ruff починен | коммит 07b1a2b |
| «Вопрос 7: расчёт HPA не по вашему выводу» | Исправлено: 75% при 2 репликах → 3; 193% при 3 → 10; 146% при 6 → ceil(6·146/60)=15 → упор в maxReplicas=6 (TooManyReplicas в describe hpa); вниз — окно стабилизации 300 с | REPORT_2.md, Вопрос 7 |
| «Нет выводов dvc push / dvc diff / dvc pull в чистом клоне; /health только после отката; run_id отредактированы» | Дополнить REPORT_2 реальными выводами команд; /health до и после отката; JSON трёх запусков с настоящими run_id и champion_before | |
| «MIN_GAIN=0.005 подобран по запускам, без осмысленного обоснования» | Исправлено: 0.005 ≈ 1% среднего Overall (3.29) и ~0.9% std таргета (0.55) — меньшая разница это шум; + оговорка про сравнение MAE между версиями данных | REPORT_2.md, раздел 2 (переписан) |
| «Вопрос 8 не отвечает, как восстановить данные версии N» | Исправлено: data_md5 из реестра → git log -p по .csv.dvc ищем коммит с этим md5 → git checkout указателя → dvc checkout → сверка md5sum | REPORT_2.md, Вопрос 8 (переписан) |

# Homework 1 Results

- терминал с выводом `uv run pytest`

![alt text](images/image.png)

- SELECT из таблицы логов (compose)

![alt text](images/image-1.png)

- `kubectl get pods` (2/2 Running) + ответ `/v1/predict` через port-forward

![alt text](images/image-2.png)
![alt text](images/image-3.png)

- k9s с подами (`:pods` или `:xray deploy`)

![alt text](images/image-4.png)


### Журнал проблем

![alt text](images/image-5.png)
-> Я создал экземпляр `features = Features()` в файле `features.py`, а затем выполнил импорт `from grade_perform.features import features` - ошибка, поэтому мне нужно импортировать только класс `Features` из `grade_perform.features`

![alt text](images/image-6.png)
-> Выключил впн

![alt text](images/image-7.png)
-> Попросил ИИ, исправление через `Set-DnsClientServerAddress -InterfaceAlias ​​"WLAN (Realtek WiFi)" -ServerAddresses 1.1.1.1,8.8.8.8`
`Clear-DnsClientCache`

![alt text](images/image-8.png)
-> Использовал команду `docker pull python:3.11-slim`

![alt text](images/image-9.png)
-> Очень долгая загрузка - сменить с COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv на COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv в dockerfile

![alt text](images/image-10.png)
-> положил COPY README ниже RUN


# Homework 2 Results

## Complete run

https://github.com/saakolch/ML_Pro_2026_assignment_1/pkgs/container/ml_pro_2026_assignment_1

![green run](images/green_run.png)

## Branch with red and green tests

pull: https://github.com/saakolch/ML_Pro_2026_assignment_1/pull/1

## 2.3  Changing model path in configMap

### Поменял ссылку, но ничего не сломалось, не очень понимаю почему, но думаю, что ссылка тащится из конфига 
![alt text](images/configMap_error.png)

## 2.3 Broken secret 

red: https://github.com/saakolch/ML_Pro_2026_assignment_1/actions/runs/36326046542/job/108639065980
-> deploy is red, можно видеть через kubectl logs <pod-name>

green: https://github.com/saakolch/ML_Pro_2026_assignment_1/actions/runs/36326320274

## 2.3 Broken memory 

red: https://github.com/saakolch/ML_Pro_2026_assignment_1/actions/runs/36326492154
-> deploy красный

green: https://github.com/saakolch/ML_Pro_2026_assignment_1/actions/runs/36326546543

### Можно видеть через kubectl get pods для статуса, kubectl describe pod <pod-name> для шага диагностики, можно видеть само приложение через kubectl logs <pod-name>

### Questions
1. 3 мин 37 сек для первого:
https://github.com/saakolch/ML_Pro_2026_assignment_1/actions/runs/36322402594
2 мин 44 сек для второго
https://github.com/saakolch/ML_Pro_2026_assignment_1/actions/runs/36324012034 
Слой из докера взят для файлов зависимостей потому что зависимости одинковые для обоих веток

2. Поды в ImagePullBackOff создаются процессом RollingUpdate, который запускает новую версию приложения, не отключая старые работающие поды. Пайплайн остается зеленым, потому что команда kubectl apply проверяет только успешную отправку конфиг в кластер, а не фактический запуск контейнеров.

3. Пароль передается из GitHub Secrets в пайплайн, который создает объект Kubernetes Secret для безопасной подстановки в переменную окружения пода. Хранить его в ConfigMap нельзя из-за риска сливания данных при коммите в репозиторий.

4. Если убрать зависимость, сборка образа build запустится параллельно с тестами, и в случае падения тестов потрачу лишнее время на сборку заведомо сломанного кода.

5. За это отвечает строка on: pull_request с фильтром по конкретным джобам, а сделано это для экономии ресурсов CI/CD, чтобы не собирать образы и не обновлять сервера до одобрения кода.

6. Блокировка предотвращает состояние race condition при одновременном запуске двух реплик приложения, без нее они обе попытались бы одновременно применить миграции к пустой базе данных и вызвали бы ошибку дублирования структур.

7. Все красные прогоны в деплой, и ошибка с ссылкой на модель (которая у меня всё равно зеленая) это возможно ошибка будет старта, ошибка скачивания секретов для датабазы, ошибка выделения ресурсов будет на request с запросом памяти выше лимитов


## Errors

#### порт сменить с 8080:80 на 8080:8000, сервис сидит на 8000
![settings](images/settings.png)

#### не добавил пароль в сетинги

![alt text](images/passport_error.png)

# Homework 3 Results

## 1. Платформа в кластере

![alt text](image.png)

### MLflow:

![alt text](image-1.png)

## 2. Обучение, реестр и гейт

### Доп картинка теста и предикта

![alt text](image-2.png)

### Min_gane

#### лучшая возможный прирост это 0.009, поэтому берем примерно половину - 0.005

![alt text](image-3.png)

### 3 запуска:

'''
{"run_id": "...", "version": "1", "alpha": 1.0, "mae": 0.1629, "promoted": true}
{"run_id": "...", "version": "2", "alpha": 100.0, "mae": 0.1838, "promoted": false}
{"run_id": "...", "version": "3", "alpha": 10.0, "mae": 0.1532, "promoted": true}
'''

## 3. Сервис по алиасу и откат модели

![alt text](image-4.png)

### 51 секунда латенс

## 4. CI/CD в свой кластер

### Link:
'''
https://github.com/saakolch/ML_Pro_2026_assignment_1/actions/runs/37215423658
'''

![alt text](image-8.png)

![alt text](image-9.png)

## 5. Версии данных в DVC

![alt text](image-6.png)

![alt text](image-7.png)


## 6. Автомасштабирование HPA

![alt text](image-10.png)

![alt text](image-11.png)

![alt text](image-12.png)


## Вопросы

'''
1. Почему tests и build в облаке GitHub, а deploy — нет? Какие ещё способы доставить код за NAT, почему runner?
Tests и build не трогают наш кластер: тесты поднимают свой postgres как service в облаке, build просто пушит образ в реестр. А deploy обязан достучаться до локального kind-кластера, который спрятан за NAT домашней машины - GitHub-раннер из облака туда не попадёт. Альтернативы: пробросить публичный IP/туннель (ngrok, port-forward). Мы выбрали runner: он живёт в docker-сети kind, видит узел кластера напрямую, и к тому же он строит образ локально — ведь наш ghcr.io из домашней сети даже недоступен.
2. Зачем runner'у --network kind, docker socket и --group-add 0?
--network kind вводит контейнер раннера в docker-сеть кластера - без этого до API-сервера kind не достучаться (NAT). Docker socket даёт раннеру доступ к демону хоста, чтобы делать docker build и docker save для загрузки образа в узел - без него ни собрать, ни передать образ. --group-add 0 добавляет процессу root-группу, потому что сокет принадлежит root — без этого каждое обращение падает с «permission denied».
3. Почему create secret заменили на --dry-run=client -o yaml | kubectl apply?
create secret — императивная команда: на втором деплое она упадёт с AlreadyExists и сломает пайплайн, а значения секрета она обновить не умеет. --dry-run=client -o yaml рендерит манифест на клиенте, а apply идемпотентен - создаёт или обновляет. Мы это увидели вживую: на повторном прогоне шаг «taking secrets» прошёл со словами secret/ci-db-secrets created / configured вместо ошибки.
4. Challenger vs champion; алиас вместо номера версии; откат алиасом vs rollout undo.
Challenger - самая свежая обученная версия (алиас вешается всегда), champion - только та, что прошла гейт (MAE лучше текущего чемпиона минимум на MIN_GAIN=0.005: 0.1443 против 0.1532). Сервис спрашивает алиас, а не версию, потому что алиас - стабильный указатель: имя grade_perform@champion всегда означает «лучшая сейчас», без правки конфига. Откат алиасом (перевесили champion на v1 → rollout restart → /health изменился с registry-v3 на registry-v1 за 51 секунду) не требует пересборки и старого образа; rollout undo откатывает код на предыдущий ReplicaSet и зависит от того, что старый образ ещё есть в кластере.
5. Что будет, если задеплоить сервис там, где модель ещё не обучали?
На старте lifespan спросит у реестра grade_perform@champion, получит MlflowException (Registered Model not found), напечатает «registry load failed» и останется без pipeline. Под отвечает на /health («not provided»), но /ready отдаёт 503 «no model is loaded», readiness-probe не проходит. В CI это видно как зависший kubectl rollout status («Waiting for deployment ... replicas to become ready») и красный деплой по таймауту.
6. Путь запроса браузер → MLflow; зачем allowed-hosts и CORS; почему порт 80 при создании кластера.
Браузер → hosts-запись (mlflow.localhost → 127.0.0.1) → порт 80 хоста → kind extraPortMappings → порт 30080 внутри узла → kube-proxy → под Traefik → по Ingress-правилу (Host: mlflow.localhost) → под MLflow на 5000. --allowed-hosts защищает от подмены заголовка Host (анти-DNS-rebinding): чужое имя получит 403. --cors-allowed-origins нужен, потому что UI MLflow — SPA, который из браузера зовёт API с другого origin; без этого браузер блокирует запросы. Порт 80 задаётся при kind create cluster, потому что это extraPortMapping — публикация порта на уровне docker у контейнера узла, добавить её работающему контейнеру нельзя, только пересоздав кластер.
7. Формула реплик: расчёт vs факт; почему вниз медленнее.
Формула: desired = ceil(текущие реплики × текущая нагрузка / target). По моим цифрам: при 2 репликах и 162% CPU (target 60%) → ceil(2×162/60) = ceil(5.4) = 6 — HPA выставил ровно 6; промежуточный скачок до 4 соответствует замеру ~120% (ceil(2×120/60)=4). Вниз ушло дольше, чем вверх: у scale-down окно стабилизации 300 секунд, и HPA не дёргает реплики на кратковременных просадках — у меня после остановки locust реплики простояли на 6 целых ~5 минут и только потом пошли 6→3→2.
8. Что в git, что в DVC; как восстановить данные модели версии N.
В git лежат код, манифесты, CI, и маленький указатель artifact/ResearchInformation3.csv.dvc (md5 + размер); сам CSV живёт в DVC-хранилище ../dvc-storage/files/md5/... . файл восстановлен байт-в-байт. В чистом клоне то же самое проверено: dvc pull выдал файл с md5 65A42FAB…, но потребовалось сначала dvc remote modify local --local url <абсолютный путь>, потому что относительный локальный remote не «переезжает» с клоном.
'''


## Ошибки

![alt text](image-5.png)

'''
Не загрузил image докера для kubernetes и исправил добавлением локальным image с kind load docker-image grade-perform:hw1 --name kind

для секретов добавить в кластер:
kubectl create secret generic grade-perform-secrets `
  --from-literal=POSTGRES_PASSWORD=yourpass `
  --from-literal=DATABASE_URL="postgresql://postgres:yourpass@postgres:5432/grade-perform"
'''


# Homework 4 Results

# 1. Платформа одной командой

![alt text](image-13.png)

# 2. Метрики и дашборд

![alt text](image-14.png)

# 3 Данные в DVC и S3 кластера 

## .dvc в репо
'''
https://github.com/saakolch/ML_Pro_2026_assignment_1/tree/main/.dvc
'''

## S3

![alt text](image-15.png)

# 4 Проверка данных

![alt text](image-15.png)

## зеленый прогон 
'''
https://github.com/saakolch/ML_Pro_2026_assignment_1/actions/runs/39270604387
'''

# 5. Конвейер переобучения в Airflow

## dag 1 

![alt text](image-17.png)

## dag 2

![alt text](image-18.png)

## dag 3

![alt text](image-16.png)

## возврат прежнего dvc поинтера и реран 

![alt text](image-19.png)

## model registry

![alt text](image-20.png)

## 6. CI/CD целиком

## link

'''
https://github.com/saakolch/ML_Pro_2026_assignment_1/actions/runs/39361233422
'''


## ошибки

## внутри kind сломан DNS 

![alt text](image-21.png)

![alt text](image-22.png)

'''
надо вписать руками traefik на хост и закинуть в docker: 
docker pull traefik:v3.7.13
kind load docker-image traefik:v3.7.13 --name sem4
'''

## kind load docker-image падает на мультиплатформенных образах

![alt text](image-23.png)

'''
сначала помещаю .tar в kind и затем запускаю скрипт - так traefik будет уже сидеть в kind до ошибки от скрипта:

docker rmi traefik:v3.7.13
docker pull traefik:v3.7.13 --platform linux/amd64
docker save --platform linux/amd64 traefik:v3.7.13 -o traefik-image.tar
kind load image-archive traefik-image.tar --name sem4
& "C:\Program Files\Git\bin\bash.exe" platform/up.sh
Remove-Item traefik-image.tar
'''

### итог

![alt text](image-24.png)

## неверный пароль при подключении к ДБ - произошла инициализация и пароль стал дефолтным

![alt text](image-25.png)

'''
перезапустил под чтобы он подтянул пароль из GitHub
'''

## снова трабл с DNS

![alt text](image-26.png)

'''
PodLaunchFailedException: Image cannot be pulled, unable to start: ErrImagePull
failed to pull and unpack image "docker.io/library/alpine:3.24.1": failed to resolve reference "docker.io/library/alpine:3.24.1": failed to do request: Head "https://registry-1.docker.io/v2/library/alpine/manifests/3.24.1": dial tcp 108.160.165.48:443: connect: connection refused
'''

'''
-> взять ту же тактику как раньше:
docker pull alpine:3.24.1 --platform linux/amd64
docker save --platform linux/amd64 alpine:3.24.1 -o "$env:TEMP\alpine.tar"
kind load image-archive "$env:TEMP\alpine.tar" --name sem4
Remove-Item "$env:TEMP\alpine.tar"
'''


## Ответы

1. У вас в реестре версия N модели. По шагам: как восстановить ровно тот код и те данные, на
которых она обучена? Какие поля прогона MLflow и какие файлы в git для этого нужны?

'''
Посмотреть хеш в строке data_md5 и git commit хеш в MLflow и далее запустить:   
git checkout <commit-hash> и dvc checkout (чтобы подгрузить нужный поинтер)
'''

2. Почему данные не в образе, а указатели в образе? Что сломается, если сделать git push
раньше dvc push, и где вы это увидите?

'''
Данные версионируются в DVC и тянутся свежими из S3 - так образ не раздувается и не пересобирается при каждой смене данных, а одна и та же выгрузка переиспользуется. Если сделать git push раньше dvc push, в прод попадёт указатель на md5, которого нет в RustFS → dvc pull -r cluster в подах упадёт с «checksum/entry not found». Будет в логах задач validate/train в Airflow (сам CI при этом будет зелёный - сборке указатель не мешает).
'''

3. Какие проверки вашей схемы бинарные, а какие с порогом? Как выбирали порог и что будет,
если он слишком строгий?

'''
Бинарные — типы колонок, strict=True, все Check.isin (Department, Gender, Hometown и тд) и диапазоны как факт (HSC/SSC/Last/Overall). Пороговые - len(df) >= 400, медиана Overall в окне 3.0–3.6, пропуски < 5%, дубликаты = 0; пороги взяты из самих данных (482 строки, медиана 3.29, пропусков 0). Слишком строгий порог даёт ложные браки: валидный сдвиг когорты будет вечно отбрасываться и DAG перестанет переобучаться без веской причины.
'''

4. Чем проверка pandera в конвейере отличается от Pydantic‐схемы в сервисе? Зачем нужны
обе?

'''
Pandera проверяет выгрузку целиком перед обучением (статистика датасета: объём, медиана, пропуски, дубликаты) — это контракт конвейера. Pydantic проверяет каждый входящий запрос в сервисе и отдаёт 422 с request_id - это API-контракт. Обе нужны, защищают сервис: конвейер от плохих данных до обучения, сервис - от невалидных запросов в рантайме.
'''

5. Почему обучение идёт в отдельном поде из образа сервиса, а не внутри Airflow? Почему
выкат новой модели не требует пересборки образа?

'''
KubernetesPodOperator даёт изоляцию ресурсов (обучение не ест память Airflow-воркера) + гарантия кода как в проде. Не нужна пересборка потому что rollout просто перезапускает деплоймент и новые поды сами забирают @champion
'''

6. Какие метрики на вашем дашборде про инфраструктуру, какие про сервис, какие про мо‐
дель? Почему request_id нельзя класть в метку Prometheus?

'''
Инфраструктура: рестарты контейнеров, RPS по обработчикам; 
сервис: число запросов к /predict, задержка p50/p95; 
модель: версия в подах, гистограмма распределения предсказаний и средний прогноз (sum/count). 
request_id нельзя в метку из-за кардинальности: каждый уникальный request_id рождает новый time series, миллионы запросов убьют Prometheus по памяти и диску; то же с уникальными значениями признаков.
'''

7. Что происходит с подами и с запросами во время выката новой модели? Зачем preStop и
что вы видели без него?

'''
Rolling update: старые поды получают SIGTERM и завершаются, новые поднимаются; 
без preStop kubelet убивает под мгновенно, а Traefik ещё шлёт на него запросы и тогда 502 и разорванные соединения на графике. preStop: sleep 5 даёт kubelet время вывести под из эндпоинтов и дописать in-flight запросы; 
с preStop при рестартах генератор не получал ни одной ошибки.
'''

8. Какой отказ вашего проекта в проде самый вероятный? Где и через сколько вы его заметите
и что сделаете первым?

'''
Под не смог загрузить модель из реестра (MLflow недоступен/алиас сломан) — в lifespan это ловится, но pipeline=None → /ready отдаёт 503 и трафик на под не идёт. 
Заметим на дашборде: версия модели обнуляется, запросы висят. 
Первое действие: kubectl logs пода → при проблеме реестра откатиться на последний рабочий champion и перезапустить деплоймент.
'''