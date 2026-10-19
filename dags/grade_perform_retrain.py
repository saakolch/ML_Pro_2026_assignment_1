"""Переобучение модели успеваемости.

validate  под с образом сервиса: dvc pull датасета из S3, проверка схемы pandera; при нарушениях код выхода 1
train     под с образом сервиса: dvc pull, обучение Ridge, гейт champion/challenger в MLflow
promoted  дальше идём, только если гейт в train.py отдал новой версии алиас champion
rollout   перезапуск grade-perform-api: новые поды загрузят нового champion из реестра

Образ для обучения берётся из переменной grade_perform_image, её выставляет CI при каждом деплое.
"""
from datetime import UTC, datetime

from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator
from airflow.sdk import CronTriggerTimetable, Param, dag, task
from kubernetes.client import models as k8s

# данных в образе нет: DVC берёт их из S3 по адресу изнутри кластера (remote cluster)
PULL = "uv run --no-sync dvc pull -r cluster datasets/ResearchInformation3.csv && "
MLFLOW = {"MLFLOW_TRACKING_URI": "http://mlflow.grade-mlops:5000"}
COMMON = {
    "namespace": "grade-mlops",
    "in_cluster": True,
    "image": "{{ var.value.grade_perform_image }}",
    "image_pull_policy": "IfNotPresent",
    "get_logs": True,
    "on_finish_action": "delete_pod",
}


def secret(name: str) -> list:
    return [k8s.V1EnvFromSource(secret_ref=k8s.V1SecretEnvSource(name=name))]


@dag(
    # раз в день в 03:00 по Москве; пропущенные запуски не догоняем
    schedule=CronTriggerTimetable("0 3 * * *", timezone="Europe/Moscow"),
    catchup=False,
    params={"alpha": Param(1.0, type="number", exclusiveMinimum=0, description="регуляризация Ridge")},
    tags=["grade_perform"],
)
def grade_perform_retrain():
    validate = KubernetesPodOperator(
        task_id="validate",
        name="grade-perform-validate",
        env_vars=MLFLOW,
        env_from=secret("s3-credentials"),
        cmds=["sh", "-c", PULL + "uv run --no-sync python -m grade_perform.data"],
        **COMMON,
    )
    train = KubernetesPodOperator(
        task_id="train",
        name="grade-perform-train",
        env_vars={**MLFLOW, "RIDGE_ALPHA": "{{ params.alpha }}"},
        env_from=secret("s3-credentials"),
        do_xcom_push=True,
        cmds=["sh", "-c", PULL + "uv run --no-sync python src/train.py"],
        **COMMON,
    )

    @task.short_circuit
    def promoted(result: dict) -> bool:
        print(f"версия {result['version']}, mae {result['mae']}, champion до этого {result['champion_before']}")
        return result["promoted"]

    @task
    def rollout():
        from kubernetes import client, config

        config.load_incluster_config()
        now = datetime.now(UTC).isoformat()
        client.AppsV1Api().patch_namespaced_deployment(
            "grade-perform-api",
            "default",
            {"spec": {"template": {"metadata": {"annotations": {"kubectl.kubernetes.io/restartedAt": now}}}}},
        )
        print("grade-perform-api перезапущен", now)

    validate >> train
    promoted(train.output) >> rollout()


grade_perform_retrain()
