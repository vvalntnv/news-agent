from core.errors.base import ErrorPayload, InternalError


class DashManifestError(InternalError):
    def __init__(
        self,
        *,
        code: str,
        message: str,
        manifest_url: str,
        details: dict[str, str] | None = None,
    ) -> None:
        payload_details: dict[str, str] = {"manifest_url": manifest_url}
        if details is not None:
            payload_details.update(details)

        super().__init__(
            internal_payload=ErrorPayload(
                code=code,
                message=message,
                details=payload_details,
            )
        )


class DashManifestParseError(DashManifestError):
    def __init__(self, manifest_url: str, parse_error: str) -> None:
        super().__init__(
            code="dash_manifest_parse_error",
            message="DASH manifest could not be parsed.",
            manifest_url=manifest_url,
            details={"parse_error": parse_error},
        )


class DashManifestMissingPeriodError(DashManifestError):
    def __init__(self, manifest_url: str) -> None:
        super().__init__(
            code="dash_manifest_missing_period",
            message="DASH manifest does not contain a Period element.",
            manifest_url=manifest_url,
        )


class DashManifestMissingAdaptationSetError(DashManifestError):
    def __init__(self, manifest_url: str) -> None:
        super().__init__(
            code="dash_manifest_missing_adaptation_set",
            message="DASH Period does not contain an AdaptationSet element.",
            manifest_url=manifest_url,
        )


class DashManifestMissingRepresentationError(DashManifestError):
    def __init__(self, manifest_url: str) -> None:
        super().__init__(
            code="dash_manifest_missing_representation",
            message="DASH AdaptationSet does not contain a Representation element.",
            manifest_url=manifest_url,
        )


class DashManifestUnsupportedStructureError(DashManifestError):
    def __init__(self, manifest_url: str, reason: str) -> None:
        super().__init__(
            code="dash_manifest_unsupported_structure",
            message="DASH manifest has unsupported structure.",
            manifest_url=manifest_url,
            details={"reason": reason},
        )


class DashManifestNoDownloadLinksError(DashManifestError):
    def __init__(self, manifest_url: str) -> None:
        super().__init__(
            code="dash_manifest_no_download_links",
            message="DASH manifest did not produce downloadable links.",
            manifest_url=manifest_url,
        )


class HlsManifestError(InternalError):
    def __init__(
        self,
        *,
        code: str,
        message: str,
        manifest_url: str,
        details: dict[str, str] | None = None,
    ) -> None:
        payload_details: dict[str, str] = {"manifest_url": manifest_url}
        if details is not None:
            payload_details.update(details)

        super().__init__(
            internal_payload=ErrorPayload(
                code=code,
                message=message,
                details=payload_details,
            )
        )


class HlsManifestNoVariantsError(HlsManifestError):
    def __init__(self, manifest_url: str) -> None:
        super().__init__(
            code="hls_manifest_no_variants",
            message="HLS master playlist does not contain variants.",
            manifest_url=manifest_url,
        )


class HlsManifestNoMediaSegmentsError(HlsManifestError):
    def __init__(self, manifest_url: str) -> None:
        super().__init__(
            code="hls_manifest_no_media_segments",
            message="HLS playlist does not contain media segments.",
            manifest_url=manifest_url,
        )


class DirectMediaInvalidUrlError(InternalError):
    def __init__(self, media_url: str) -> None:
        super().__init__(
            internal_payload=ErrorPayload(
                code="direct_media_invalid_url",
                message="Direct media url is invalid.",
                details={"media_url": media_url},
            )
        )


class MediaMuxNoChunksError(InternalError):
    def __init__(self, source_url: str) -> None:
        super().__init__(
            internal_payload=ErrorPayload(
                code="media_mux_no_chunks",
                message="Cannot mux media without downloaded chunks.",
                details={"source_url": source_url},
            )
        )


class FFmpegExecutionError(InternalError):
    def __init__(self, command: list[str], return_code: int, stderr: str) -> None:
        super().__init__(
            internal_payload=ErrorPayload(
                code="ffmpeg_execution_error",
                message="ffmpeg command execution failed.",
                details={
                    "return_code": str(return_code),
                    "command": " ".join(command),
                    "stderr": stderr,
                },
            )
        )


class MediaMuxChunksInDifferentPathsError(InternalError):
    def __init__(self, chunk1_path: str, chunk2_path: str) -> None:
        super().__init__(
            internal_payload=ErrorPayload(
                code="media_mux_chunks_in_different_paths",
                message="All chunks must be in the same directory for concatenation.",
                details={
                    "chunk1_path": chunk1_path,
                    "chunk2_path": chunk2_path,
                },
            )
        )


class MediaMuxChunksDifferentExtensionsError(InternalError):
    def __init__(self, chunk1_extension: str, chunk2_extension: str) -> None:
        super().__init__(
            internal_payload=ErrorPayload(
                code="media_mux_chunks_different_extensions",
                message="All chunks must have the same file extension for concatenation.",
                details={
                    "chunk1_extension": chunk1_extension,
                    "chunk2_extension": chunk2_extension,
                },
            )
        )


class MediaMuxMissingInitializationSegmentError(InternalError):
    def __init__(self, chunk_count: int) -> None:
        super().__init__(
            internal_payload=ErrorPayload(
                code="media_mux_missing_initialization_segment",
                message="Cannot mux media without an initialization segment.",
                details={
                    "chunk_count": str(chunk_count),
                },
            )
        )
