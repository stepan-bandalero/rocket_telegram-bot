from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    bot_token: str
    db_dsn: str
    admins: list[int] = []

    class Config:
        env_file = ".env"


settings = Settings()
