from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_nested_delimiter="__")

    scrapers_info_dir: Path = Path("./sites")


config = Config()
