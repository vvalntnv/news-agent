from application.ai.workflow.predefined.news_site_exploration.models import (
    NewsSiteExplorationInput,
)
from domain.news.value_objects import ScrapeInformation


def build_feed_exploration_prompt(
    input_data: NewsSiteExplorationInput,
    attempt_number: int,
) -> str:
    lines: list[str] = [
        "Explore the news website and extract feed-level CSS selectors for scraping.",
        f"Target URL: {input_data.scraping_url}",
        f"Attempt number: {attempt_number}",
        "Return only a valid ScrapeInformation object.",
        "Workflow context: this is phase 1 of 2.",
        "Phase 1 discovers feed-level selectors to collect article URLs and metadata from listing pages.",
        "Phase 2 will refine article-level selectors using sampled article pages.",
        "Selectors must be specific and stable across pages.",
        "Prefer class/id/semantic anchors over structural depth.",
        "Avoid deeply nested positional chains.",
        "Forbidden pattern examples: `main > div > div > div`, `body > div:nth-child(3) > ...`.",
        "Use only valid CSS selectors and keep them deterministic.",
        "For this step, prioritize articleContainers, titlesContainers, timestampsConteiners, and summaryContainers.",
        "Do not touch `mainArticleContainer` yet; main_article_container should remain unset until we explore individual articles.",
        "When media is unavailable, use null for imageContainers/videoContainers/audioContainers.",
        "Use timestampsConteiners exactly as defined in the schema.",
    ]

    if input_data.extra_guidance is not None:
        lines.append(f"Additional guidance: {input_data.extra_guidance}")

    return "\n".join(lines)


def build_article_exploration_prompt(
    *,
    input_data: NewsSiteExplorationInput,
    attempt_number: int,
    partial_result: ScrapeInformation,
    sample_article_urls: list[str],
    previous_validation_error: str | None = None,
) -> str:
    lines: list[str] = [
        "Use the sampled article URLs to complete the missing scraping selectors.",
        f"Target URL: {input_data.scraping_url}",
        f"Attempt number: {attempt_number}",
        "Workflow context: this is phase 2 of 2.",
        "These selectors are production selectors and will be reused for future articles, not just the sampled pages.",
        "Use the browse tool to inspect each sampled article URL with sanitize=true.",
        "The browse tool accepts only these arguments: `site_url`, `sanitize`, `root_of_analysis`.",
        "Do not pass any other arguments to browse (forbidden examples: `pattern`, `selector`, `css`).",
        "Prefer root_of_analysis='article' and retry with root_of_analysis='body' when needed.",
        "Return only a valid ScrapeInformation object.",
        "Selectors must be specific and stable across many articles, not just one article page.",
        "Prefer class/id/semantic anchors over structural depth.",
        "Avoid deeply nested positional chains.",
        "Forbidden pattern examples: `main > div > div > div`, `body > div:nth-child(3) > ...`.",
        "Never use positional pseudo selectors such as `:first-of-type`, `:last-of-type`, `:nth-child(...)`, `:nth-of-type(...)` for production selectors.",
        "Use only valid CSS selectors and keep them deterministic.",
        "Be as precise as possible and include as many relevant selectors as needed for author, timestamp, and summary fields, even if they share the same container; document each identifier explicitly.",
        "While the page might show multiple authors/timestamps, pinpoint the single author and timestamp belonging to the article content-not global site attribution or unrelated widgets.",
        "`mainArticleContainer` will be used later to scrape ALL future article pages, so it must generalize beyond the sampled pages.",
        "You must compare all provided sample article URLs and pick one selector that consistently matches the main article content container across all of them.",
        "A selector is acceptable only if it is valid for every sampled article URL.",
        "If one sample fails, you must refine the selector until all samples are covered.",
        "Do not choose page-instance-specific wrappers that exist only in one sample page.",
        "`mainArticleContainer` must not be a brittle chain of generic tags.",
        "For `authorContainer`, avoid link selectors that rely on href fragments plus positional pseudo selectors.",
        "Prefer stable author/byline classes, ids, roles, itemprop attributes, or other semantic anchors.",
        "Before finalizing, mentally validate the selector against every sample URL and keep it only if it remains consistent.",
        "All required fields must be present and non-empty where applicable.",
        "Keep already correct selectors and improve only what is missing or unstable.",
        "Current ScrapeInformation draft:",
        partial_result.model_dump_json(by_alias=True),
        "Sample article URLs:",
        "\n".join(sample_article_urls),
    ]

    if input_data.extra_guidance is not None:
        lines.append(f"Additional guidance: {input_data.extra_guidance}")

    if (
        previous_validation_error is not None
        and previous_validation_error.strip() != ""
    ):
        lines.append("Previous validation failed. You must fix this exactly:")
        lines.append(previous_validation_error)

    return "\n".join(lines)
