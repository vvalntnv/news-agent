from pydantic import BaseModel, Field

from domain.news.value_objects import ScrapeInformation


class NewsSiteExplorationInput(BaseModel):
    scraping_url: str = Field(min_length=1)
    max_attempts: int = Field(default=2, ge=1, le=5)
    sample_articles_count: int = Field(default=2, ge=1, le=5)
    extra_guidance: str | None = None
    example_articles: list[str] = Field(default_factory=list)


class NewsSiteExplorationDependencies(BaseModel):
    scraping_url: str


class NewsSiteExplorationState(BaseModel):
    input_data: NewsSiteExplorationInput
    scraping_url: str
    max_attempts: int
    article_refinement_attempts: int = 0
    last_validation_error: str | None = None
    sample_articles_count: int
    sample_article_urls: list[str] = Field(default_factory=list)
    latest_result: ScrapeInformation | None = None
