from pydantic import BaseModel
from pydantic_core import Url


class TimedMedia(BaseModel):
    url: Url
    length_in_seconds: int


class VideoData(TimedMedia): ...


class AudioData(TimedMedia): ...
