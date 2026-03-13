from typing import Self
import httpx
from pydantic_ai import RunContext

from application.ai.workflow.predefined.news_site_exploration import (
    NewsSiteExplorationDependencies,
)
from core.config import config
from domain.ai.protocols import Tool
from domain.ai.tool_schema_mixin import ToolSchemaMixin
from infrastructure.extraction.html_sanitizer import HtmlSanitizer, RootOfAnalysis


class BrowseTool(ToolSchemaMixin, Tool):
    name = "browse"
    description = "Browse a website and retrieve all of its contents."
    ctx_type = NewsSiteExplorationDependencies

    @classmethod
    def build_with_client(
        cls,
        sanitizer: HtmlSanitizer | None = None,
    ) -> tuple[Self, httpx.AsyncClient]:
        client = httpx.AsyncClient(
            headers={
                "User-Agent": config.media_http_user_agent,
                "Accept": "text/html,application/xhtml+xml",
            },
            follow_redirects=config.media_http_follow_redirects,
            timeout=config.media_http_timeout_seconds,
        )

        return cls(client, sanitizer), client

    def __init__(
        self,
        client: httpx.AsyncClient,
        sanitizer: HtmlSanitizer | None = None,
    ) -> None:
        super().__init__()
        self.sanitizer = sanitizer or HtmlSanitizer()
        self.client = client

    async def __call__(
        self,
        ctx: RunContext[NewsSiteExplorationDependencies],
        *,
        site_url: str | None = None,
        sanitize: bool,
        root_of_analysis: RootOfAnalysis | None = None,
    ) -> str:
        target_url = self._resolve_site_url(
            site_url=site_url,
            fallback_url=ctx.deps.scraping_url,
        )

        response = await self.client.get(target_url)
        response.raise_for_status()

        page_html = response.text
        if not sanitize:
            return page_html

        return self.sanitizer.sanitize_html(
            page_html,
            root_of_analysis=root_of_analysis,
        )

    def _resolve_site_url(self, *, site_url: str | None, fallback_url: str) -> str:
        if site_url is None:
            return fallback_url.strip()

        normalized_site_url = site_url.strip()
        if normalized_site_url == "":
            return fallback_url.strip()

        return normalized_site_url
