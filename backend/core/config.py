from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv
from pathlib import Path
from urllib.parse import quote

load_dotenv()


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_nested_delimiter="__")

    scrapers_info_dir: Path = Path("./sites")
    db_user: str = "postgres"
    db_pass: str = "postgres"
    db_host: str = "localhost"
    db_port: str = "5432"
    db_name: str = "news_agent"

    @property
    def db_url(self) -> str:
        return (
            f"postgres://{quote(self.db_user)}:{quote(self.db_pass)}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def tortoise_orm(self) -> dict[str, dict[str, object]]:
        return {
            "connections": {"default": self.db_url},
            "apps": {
                "models": {
                    "models": ["infrastructure.database.models", "aerich.models"],
                    "default_connection": "default",
                },
            },
        }


config = Config()
