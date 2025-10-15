# from pydantic import BaseSettings
from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    APP_NAME: str = "IA Auditoría Colsubsidio"
    ENV_NAME: str = "development"
    API_V1_STR: str = "/api/v1"

    # Rutas (seguros para Pylance y multiplataforma)
    BASE_DIR: str = str(Path(__file__).resolve().parents[2])  # sube desde core -> app -> backend
    DATA_DIR: str = str(Path(BASE_DIR) / "data" / "pdfs")
    UPLOAD_DIR: str = str(Path(BASE_DIR) / "uploads")

    class Config:
        env_file = ".env"

settings = Settings()

