# Assignment 3

## 1. Платформа в кластере

![alt text](image.png)

### MLflow:

![alt text](image-1.png)

## 2. Обучение, реестр и гейт

### Доп картинка теста и предикта

![alt text](image-2.png)

### Min_gane

#### MIN_GAIN=0.005 — это ~1% среднего Overall (3.29) и ~0.9% стандартного отклонения таргета (0.55): улучшение MAE меньше порога считаю статистическим шумом, а не вкладом модели; при этом порог достаточно мал, чтобы не блокировать реальные улучшения от гиперпараметров. Оговорка: MAE текущего чемпиона берётся из его прогона — тестовая выборка той версии данных; после смены версии данных сравнение приближённое, и именно порог не даёт случайным колебаниям MAE между версиями данных пролезать как «улучшение».

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
Формула: desired = ceil(текущие реплики × текущая нагрузка / target 60%). По моим замерам: при 2 репликах CPU 75% → ceil(2×75/60) = 3; при 3 репликах 193% → ceil(3×193/60) = 10; при 6 репликах 146% → ceil(6×146/60) = 15 — желаемое превысило maxReplicas=6, HPA упёрся в максимум: в describe hpa видно ScalingLimited (TooManyReplicas), желаемое 15 ограничено шестью. Вниз после остановки locust реплики не менялись ~5 минут (окно стабилизации 300 секунд), и HPA не дёргает реплики на кратковременных просадках — потом 6→3→2.
8. Что в git, что в DVC; как восстановить данные модели версии N.
В git лежат код, манифесты, CI и указатель datasets/ResearchInformation3.csv.dvc (md5 + размер); сам CSV — в DVC-хранилище (S3 кластера, бакет dvc). Восстановление данных версии N по шагам: 1) взять data_md5 из прогона версии N в MLflow; 2) найти коммит, где .csv.dvc содержит этот md5: git log -p -- datasets/ResearchInformation3.csv.dvc; 3) git checkout <commit> -- datasets/ResearchInformation3.csv.dvc; 4) dvc checkout — файл восстанавливается из кэша/S3 байт-в-байт; 5) сверить md5sum файла с data_md5. Код той версии — git checkout <commit прогона>.
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