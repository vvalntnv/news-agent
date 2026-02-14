# Media Download Pipeline

This document describes the media pipeline that resolves stream URLs, downloads
media files/chunks, muxes/compresses the final output, and serves the result
through FastAPI static files.

## High-Level Flow

1. Scraping returns media URLs.
2. `MediaDownloadHandler` receives those URLs.
3. A matching resolver parses each URL into downloadable links.
4. A downloader fetches files/chunks into a temporary working directory.
5. A muxer uses ffmpeg to combine/compress into a final `.mp4`.
6. The output is written under `backend/static/media/`.
7. FastAPI serves files from `/static`.

## Components

### Domain Models

Defined in `backend/domain/media/value_objects.py`:

- `MediaDownloadableLink`: one downloadable URL with sequence metadata.
- `ResolvedMediaStream`: output from a resolver.
- `DownloadedMediaChunk`: one locally downloaded file.
- `DownloadedMedia`: downloader result.
- `MuxedMedia`: final output metadata after muxing.

### Protocols

Defined in `backend/domain/media/protocols.py`:

- `StreamResolverProtocol`: `can_resolve()` and `resolve_stream()`.
- `VideoDownloaderProtocol`: downloads resolved links.
- `MediaMuxerProtocol`: muxes/compresses into final output.

### Resolvers

Located in `backend/infrastructure/media/resolvers/`:

- `DirectMP4Resolver`
  - Handles direct file URLs.
  - Produces a single download link.
- `HlsM3U8Resolver`
  - Handles HLS master/media playlists.
  - Picks the highest bandwidth variant in master playlists.
  - Produces segment links (and init segment if present).
- `DashMPDResolver`
  - Handles DASH MPD manifests.
  - Supports common `SegmentList` and `SegmentTemplate` formats.
  - Produces init/media segment links.
  - Detects single-file DASH representations (including `mediaRange` segment lists)
    and downloads only the representation file.

### Downloaders

Located in `backend/infrastructure/media/downloaders/`:

- `VideoDownloader`
  - Downloads resolved links to a local folder.
  - Preserves ordering via sequence numbers and init segment ordering.
  - Returns `DownloadedMedia`.

`AudioDownloader` and `ImageDownloader` currently reuse the same chunk download
mechanism.

### Muxer

Located in `backend/infrastructure/media/muxers/video_muxer.py`:

- `VideoMuxer`
  - Keeps one orchestration entry point for all stream types.
  - Selects a stream-type-specific ffmpeg command class and executes it.
  - Uses thread count `max(1, os.cpu_count() // 2)`.
  - Writes to `static/media/`.

Command classes are located in
`backend/infrastructure/media/muxers/ffmpeg/`:

- `DirectFileCompression`
  - Used for `SupportedStreamTypes.DIRECT`.
  - Expects exactly one downloaded chunk and compresses it to `.mp4`.
- `HLSFFMpegConcat`
  - Used for `SupportedStreamTypes.HLS`.
  - Builds a temporary ffmpeg concat input list and muxes/compresses to `.mp4`.
- `DASHFFMpegConcat`
  - Used for `SupportedStreamTypes.DASH`.
  - Concatenates initialization/media bytes through stdin and muxes/compresses to
    `.mp4`.

Shared ffmpeg output/transcode arguments are centralized in
`BaseFFMpegCommand` and read from `backend/core/config.py`.

## Orchestration

`backend/application/media_download_handler.py` includes:

- `MediaDownloadHandler`
  - Selects resolver per URL.
  - Runs resolver -> downloader -> muxer.
  - Returns `MuxedMedia` for each input URL.
- `mount_static_files(app, static_root=Path("static"))`
  (defined in `backend/application/endpoints/static_files.py`)
  - Mounts FastAPI static serving at `/static`.

## FastAPI Integration Example

```python
from fastapi import FastAPI

from application.endpoints.static_files import mount_static_files
from application.media_download_handler import MediaDownloadHandler

app = FastAPI()
mount_static_files(app)

handler = MediaDownloadHandler()


@app.post("/media/download")
async def download_media(urls: list[str]) -> list[dict[str, str]]:
    outputs = await handler.download_media(urls)
    return [
        {
            "source_url": output.source_url,
            "output_path": str(output.output_path),
            "static_url": output.static_url_path,
        }
        for output in outputs
    ]
```

## Output Location

- Relative app path: `backend/static/media/`
- Public URL prefix: `/static/media/`

## Notes

- The pipeline normalizes outputs to `.mp4`.
- DASH parsing failures raise internal custom errors in `backend/core/errors/`.
- ISO 8601 duration parsing is shared in `backend/core/utils/iso.py`.
- ffmpeg must be installed and available in `PATH`.
- Unit tests for resolvers/downloaders/muxer/handler are in `backend/tests/`.
