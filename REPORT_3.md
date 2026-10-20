# Assignment 4

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

# 6. CI/CD целиком

## link

'''
https://github.com/saakolch/ML_Pro_2026_assignment_1/actions/runs/39361233422
'''


# ошибки

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


# Ответы

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