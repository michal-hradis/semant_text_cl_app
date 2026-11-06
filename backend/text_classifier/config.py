from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    # Env vars override values from .env (in the working directory; gitignored, keep secrets there).
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

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
    # Voice comments (see docs/voice_comments.md)
    VOICE_COMMENTS_ENABLED: bool = True
    VOICE_AUDIO_PATH: str = "./voice_audio"
    VOICE_MAX_SECONDS: int = 300
    VOICE_MAX_BYTES: int = 25 * 1024 * 1024  # OpenAI transcription upload limit
    # Off until recordings are validated; audio is stored and stays `pending`.
    TRANSCRIBE_ENABLED: bool = False
    OPENAI_API_KEY: str = ""
    OPENAI_TRANSCRIBE_MODEL: str = "gpt-4o-transcribe"
    TRANSCRIBE_INTERVAL_SECONDS: int = 30
    TRANSCRIBE_MAX_ATTEMPTS: int = 3


config = Config()
