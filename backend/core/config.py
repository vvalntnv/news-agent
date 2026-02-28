from pathlib import Path
from urllib.parse import quote

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class ProviderSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    api_key: str | None = None
    api_base_url: str | None = None
    api_version: str | None = None
    organization: str | None = None
    timeout_seconds: float = Field(60.0, gt=0.0)
    max_retries: int = Field(2, ge=0)
    headers: dict[str, str] = Field(default_factory=dict)


class ModelDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_name: str
    display_name: str | None = None
    temperature: float = Field(1.0, ge=0.0, le=2.0)
    top_p: float = Field(1.0, ge=0.0, le=1.0)
    max_tokens: int = Field(512, ge=1)
    timeout_seconds: float = Field(60.0, gt=0.0)
    stop_sequences: list[str] = Field(default_factory=list)
    metadata: dict[str, str] = Field(default_factory=dict)


class ProviderModelsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    settings: ProviderSettings = ProviderSettings(timeout_seconds=60.0, max_retries=2)
    default_model: str | None = None
    models: dict[str, ModelDefinition] = Field(default_factory=dict)


class ModelConfigs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    default_provider: str | None = None
    providers: dict[str, ProviderModelsConfig] = Field(default_factory=dict)

    def get_provider(self, provider_name: str) -> ProviderModelsConfig | None:
        return self.providers.get(provider_name)

    def get_model(
        self,
        *,
        provider_name: str,
        model_alias: str | None = None,
    ) -> ModelDefinition | None:
        provider_config = self.get_provider(provider_name)
        if provider_config is None:
            return None

        selected_alias = model_alias or provider_config.default_model
        if selected_alias is None:
            return None

        return provider_config.models.get(selected_alias)


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_nested_delimiter="__")

    scrapers_info_dir: Path = Path("./sites")
    static_mount_path: str = "/static"
    media_static_url_prefix: str = "/static/media"
    static_root: Path = Path("static")
    media_static_root: Path = Path("static/media")
    media_download_root: Path = Path("tmp/media-downloads")
    media_download_max_concurrency: int = 4
    media_download_retry_max_attempts: int = 3
    media_download_retry_base_backoff_seconds: float = 0.5
    media_download_retry_max_backoff_seconds: float = 10.0
    media_download_retry_jitter_ratio: float = 0.25
    media_download_retryable_status_codes: tuple[int, ...] = Field(
        default_factory=lambda: (429, 502, 503, 504)
    )
    media_download_retry_fallback_penalty_seconds: float = 2.0
    media_http_user_agent: str = "Mozilla/5.0 (compatible; NewsAgent/1.0)"
    media_http_follow_redirects: bool = True
    media_http_timeout_seconds: float = 30.0
    media_http_accept_hls: str = (
        "application/vnd.apple.mpegurl,application/x-mpegURL,text/plain"
    )
    media_http_accept_dash: str = "application/dash+xml,application/xml,text/xml"
    ffmpeg_binary: str = "ffmpeg"
    ffmpeg_threads: int | None = None
    ffmpeg_video_codec: str = "libx264"
    ffmpeg_video_preset: str = "veryfast"
    ffmpeg_video_crf: int = 23
    ffmpeg_audio_codec: str = "aac"
    ffmpeg_audio_bitrate: str = "128k"
    ffmpeg_movflags: str = "+faststart"
    dash_concat_chunk_size_bytes: int = 5 * 2**20
    db_user: str = "postgres"
    db_pass: str = "postgres"
    db_host: str = "localhost"
    db_port: str = "5432"
    db_name: str = "news_agent"

    should_remove_downloaded_media: bool = False

    models: ModelConfigs | None = None

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
