from core.errors.base import ErrorPayload, InternalError


class MissingTitleError(InternalError):
    def __init__(
        self,
        scraping_url: str,
        href: str,
        selectors: list[str],
    ) -> None:
        details = {
            "scraping_url": scraping_url,
            "href": href,
            "selectors": ", ".join(selectors),
        }
        super().__init__(
            internal_payload=ErrorPayload(
                code="missing_title",
                message="Title could not be extracted from link.",
                details=details,
            )
        )


class MissingArticleContentError(InternalError):
    def __init__(self, scraping_url: str, selector: str) -> None:
        details = {
            "scraping_url": scraping_url,
            "selector": selector,
        }
        super().__init__(
            internal_payload=ErrorPayload(
                code="missing_article_content",
                message="There is no available article content for this news.",
                details=details,
            )
        )


class MissingAuthorError(InternalError):
    def __init__(self, scraping_url: str, selector: str) -> None:
        details = {
            "scraping_url": scraping_url,
            "selector": selector,
        }
        super().__init__(
            internal_payload=ErrorPayload(
                code="missing_author",
                message="Author could not be extracted from the page.",
                details=details,
            )
        )


class NoScraperFoundError(InternalError):
    def __init__(self, url: str, host: str) -> None:
        details = {
            "url": url,
            "host": host,
        }
        super().__init__(
            internal_payload=ErrorPayload(
                code="no_scraper_found",
                message="No relevant scraper found for this news website.",
                details=details,
            )
        )
