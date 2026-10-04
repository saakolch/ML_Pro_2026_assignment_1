# Assignment 3

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



## Вопросы

'''

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