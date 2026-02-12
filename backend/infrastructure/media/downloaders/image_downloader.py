from domain.media.protocols import ImageDownloaderProtocol


class AudioDownloader(ImageDownloaderProtocol):
    def __init__(self) -> None:
        super().__init__()
