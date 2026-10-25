# Assignment 2

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
1. Время job build: 13 с и 19 с (прогоны https://github.com/saakolch/ML_Pro_2026_assignment_1/actions/runs/36322402594 и https://github.com/saakolch/ML_Pro_2026_assignment_1/actions/runs/36324012034) — слой зависимостей вынесен выше слоя кода, поэтому повторные сборки берут кэш слоёв; холодная сборка — 47 с (прогон https://github.com/saakolch/ML_Pro_2026_assignment_1/actions/runs/36314772071). 3 мин 37 с и 2 мин 44 с — это время всего прогона вместе с тестами и deploy, а не сборки.

2. Поды в ImagePullBackOff — это поды СТАРОГО ReplicaSet с образом grade-perform:hw1: они остались после шага kubectl apply и до kubectl set image, RollingUpdate не удаляет старые поды сразу. Прогон остаётся зелёным, потому что kubectl apply проверяет только успешное применение конфигурации в кластер; за фактический запуск новых подов отвечает следующий шаг kubectl rollout status — вот он и ждёт/падает по таймауту, если новые поды не стали Ready.

3. Пароль передается из GitHub Secrets в пайплайн, который создает объект Kubernetes Secret для безопасной подстановки в переменную окружения пода. Хранить его в ConfigMap нельзя из-за риска сливания данных при коммите в репозиторий.

4. Если убрать зависимость, сборка образа build запустится параллельно с тестами, и в случае падения тестов потрачу лишнее время на сборку заведомо сломанного кода.

5. За это отвечает строка on: pull_request с фильтром по конкретным джобам, а сделано это для экономии ресурсов CI/CD, чтобы не собирать образы и не обновлять сервера до одобрения кода.

6. Блокировка предотвращает состояние race condition при одновременном запуске двух реплик приложения, без нее они обе попытались бы одновременно применить миграции к пустой базе данных и вызвали бы ошибку дублирования структур.

7. Все поломки видны красными в job deploy, и причина читается по логу шага, не заглядывая в diff: неверный путь к модели (ConfigMap) — под в CreateContainerConfigError/CrashLoopBackOff, причём kubectl logs при CreateContainerConfigError ничего не покажет (контейнер не создан) — смотрим kubectl describe pod; несовпадающее имя secretRef — та же картина с «secret not found» в describe; requests памяти больше, чем есть на узле, — под остаётся в Pending, в describe видно «Insufficient memory». Шаг диагностики в deploy печатает pods/decribe/logs автоматически при падении.


## Errors

#### порт сменить с 8080:80 на 8080:8000, сервис сидит на 8000
![settings](images/settings.png)

#### не добавил пароль в сетинги

![alt text](images/passport_error.png)