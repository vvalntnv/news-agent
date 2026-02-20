from enum import Enum


class SupportedStreamTypes(str, Enum):
    HLS = "hls"
    DASH = "dash"
    DIRECT = "direct"
