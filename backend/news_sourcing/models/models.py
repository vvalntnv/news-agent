from pydantic import BaseModel, Field
from core.config import config


class News(BaseModel):
    title: str
    link: str


class ScrapeInformation(BaseModel):
    scraping_url: str = Field(alias="scrapingUrl")
    article_containers: list[str] = Field(alias="articleContainers")
    titles_containers: list[str] = Field(alias="titlesContainers")
    timestamps_conteiners: list[str] = Field(alias="timestampsConteiners")
    summary_containers: list[str] = Field(alias="summaryContainers")
    main_article_container: str = Field(alias="mainArticleContainer")
    author_container: str = Field(alias="authorContainer")


class RSSInformation(BaseModel):
    rss_feed: str = Field(alias="rssFeed")
