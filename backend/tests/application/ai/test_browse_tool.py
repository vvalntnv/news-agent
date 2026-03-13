from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic_ai import RunContext

from application.ai.tools.browse import BrowseTool
from application.ai.workflow.predefined.news_site_exploration import (
    NewsSiteExplorationDependencies,
)

pytestmark = pytest.mark.anyio


def _build_tool_context(
    scraping_url: str,
) -> RunContext[NewsSiteExplorationDependencies]:
    return cast(
        RunContext[NewsSiteExplorationDependencies],
        SimpleNamespace(
            deps=NewsSiteExplorationDependencies(scraping_url=scraping_url)
        ),
    )


async def test_browse_tool_returns_raw_html_when_sanitize_is_false() -> None:
    tool, client = BrowseTool.build_with_client()
    mock_response = MagicMock()
    mock_response.text = "<html><body><script>keep raw</script></body></html>"
    mock_response.raise_for_status = MagicMock()
    client.get = AsyncMock(return_value=mock_response)

    output = await tool(
        _build_tool_context("https://deps.example"),
        site_url="https://site.example",
        sanitize=False,
    )

    assert "<script>keep raw</script>" in output
    client.get.assert_awaited_once_with("https://site.example")
    await client.aclose()


async def test_browse_tool_sanitizes_html_with_configured_root() -> None:
    tool, client = BrowseTool.build_with_client()
    mock_response = MagicMock()
    mock_response.text = """
    <html>
      <head><title>Sample</title></head>
      <body class="page">
        <article class="news"><a href="/story" rel="nofollow">Story</a><script>bad()</script></article>
      </body>
    </html>
    """
    mock_response.raise_for_status = MagicMock()
    client.get = AsyncMock(return_value=mock_response)

    output = await tool(
        _build_tool_context("https://deps.example"),
        site_url="https://site.example",
        sanitize=True,
        root_of_analysis="article",
    )

    assert output.startswith("<article")
    assert "script" not in output
    assert 'href="/story"' in output
    assert "rel=" not in output
    assert "class=" not in output
    await client.aclose()


async def test_browse_tool_uses_context_url_when_site_url_missing() -> None:
    tool, client = BrowseTool.build_with_client()
    mock_response = MagicMock()
    mock_response.text = "<html><body><p>content</p></body></html>"
    mock_response.raise_for_status = MagicMock()
    client.get = AsyncMock(return_value=mock_response)

    output = await tool(
        _build_tool_context("https://from-deps.example"),
        sanitize=False,
    )

    assert "content" in output
    client.get.assert_awaited_once_with("https://from-deps.example")
    await client.aclose()
