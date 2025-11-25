from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # 시스템 환경변수 적용
    FRONTEND_HOST: str
    LLMSERVER_URL: str
    DATABASE_URL: str
    FAQ_DATABASE_URL: str
    HTTPX_TIMEOUT: float
    ENVIRONMENT: str = "development"

    # .env 환경변수 파일 로드
    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True
    )

# 변수로 저장하여 사용
settings = Settings()