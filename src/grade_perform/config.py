from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_path: str = "artifact/ridge_model.joblib"
    database_url: str | None = None
    model_name: str | None = None
    model_alias: str = "champion"
    mlflow_tracking_uri: str | None = None

    model_config = {"env_file": ".env"}

settings = Settings()