from pydantic import BaseModel
from pydantic_core import Url

class DownloadableLink(BaseModel):
    size_in_bytes: int
    url: Url

class TimedMedia(BaseModel):
    url: Url
    length_in_seconds: int


class VideoData(TimedMedia): ...


class AudioData(TimedMedia): ...
