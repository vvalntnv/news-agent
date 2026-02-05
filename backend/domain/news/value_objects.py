from urllib.parse import urlparse
from pydantic import BaseModel, Field, ValidationError


class Information(BaseModel):
    def get_host(self) -> str:
        url = None
        if hasattr(self, "scraping_url"):
            url = getattr(self, "scraping_url", None)
        else:
            url = getattr(self, "rss_feed", None)

        if url is None:
            raise ValidationError("no url provided")

        assert isinstance(url, str)
        hostname = urlparse(url).hostname

        assert hostname is not None
        return hostname


class ScrapeInformation(Information):
    scraping_url: str = Field(alias="scrapingUrl")
    article_containers: list[str] = Field(alias="articleContainers")
    titles_containers: list[str] = Field(alias="titlesContainers")
    timestamps_conteiners: list[str] = Field(alias="timestampsConteiners")
    video_containers: list[str] | None = Field(alias="videoContainers", default=None)
    summary_containers: list[str] = Field(alias="summaryContainers")
    main_article_container: str = Field(alias="mainArticleContainer")
    author_container: str = Field(alias="authorContainer")


class RSSInformation(Information):
    rss_feed: str = Field(alias="rssFeed")
