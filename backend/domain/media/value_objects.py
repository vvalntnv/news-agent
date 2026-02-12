from pathlib import Path

from pydantic import BaseModel, Field

from domain.media.supported_media_types import SupportedStreamTypes


class MediaDownloadableLink(BaseModel):
    url: str
    size_in_bytes: int | None = None
    sequence_number: int = 0
    is_initialization_segment: bool = False


class TimedMedia(BaseModel):
    url: str
    length_in_seconds: int


class VideoData(TimedMedia):
    pass


class AudioData(TimedMedia):
    pass


class ResolvedMediaStream(BaseModel):
    source_url: str
    stream_type: SupportedStreamTypes
    links: list[MediaDownloadableLink] = Field(default_factory=list)
    is_chunked: bool = False


class DownloadedMediaChunk(BaseModel):
    source_url: str
    file_path: Path
    sequence_number: int
    is_initialization_segment: bool = False


class DownloadedMedia(BaseModel):
    source_url: str
    stream_type: SupportedStreamTypes
    chunks: list[DownloadedMediaChunk] = Field(default_factory=list)


class MuxedMedia(BaseModel):
    source_url: str
    stream_type: SupportedStreamTypes
    output_path: Path
    static_url_path: str


class DownloadableLink(MediaDownloadableLink):
    pass
