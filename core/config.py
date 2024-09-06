from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "FastAPI Assistant API"
    LOG_LEVEL: str = "INFO"
    PROJECT_VERSION: str = "1.0.1"
    API_URL: str
    API_KEY: str
    CLIENT_NAME: str
    REDIS_URL: str

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
