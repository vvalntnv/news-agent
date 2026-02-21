from __future__ import annotations

import httpx


def build_http_status_error(
    status_code: int,
    headers: dict[str, str] | None = None,
) -> httpx.HTTPStatusError:
    request = httpx.Request("GET", "https://example.com")
    response_headers = headers or {}
    response = httpx.Response(
        status_code=status_code,
        request=request,
        headers=response_headers,
    )
    return httpx.HTTPStatusError("error", request=request, response=response)
