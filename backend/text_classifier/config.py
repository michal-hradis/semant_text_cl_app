from pydantic_settings import BaseSettings


class Config(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///database.sqlite"
    PRODUCTION: bool = False
    PORT: int = 8003
    ALLOWED_ORIGIN: str = "http://pchradis2.fit.vutbr.cz:9005"
    JWT_PRIVATE_KEY: str = "supersecret"
    SECRET: str = "sasd654fas6df54as96d8f7as9df4as6d4as65d4f6asdf65g4"
    ADMIN: str = "admin@example.com"
    ADMIN_PASSWORD: str = "admin123"
    STATIC_PATH: str = "./static"
    # Seconds a served text stays soft-reserved for the user (see reservations.py)
    RESERVATION_TTL_SECONDS: int = 900


config = Config()
