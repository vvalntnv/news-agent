from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv
from pathlib import Path
from urllib.parse import quote

load_dotenv()


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
