from pydantic import BaseModel, ConfigDict, Field

from domain.media.supported_media_types import SupportedStreamTypes


class MediaDownloadJobPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_urls: list[str] = Field(min_length=1)


class MediaDownloadJobOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_url: str
    stream_type: SupportedStreamTypes
    output_path: str
    static_url_path: str


class MediaDownloadJobResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    outputs: list[MediaDownloadJobOutput] = Field(default_factory=list)
