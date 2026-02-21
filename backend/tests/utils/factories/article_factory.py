from __future__ import annotations

from dataclasses import dataclass

from faker import Faker

from domain.news.entities import Article
from domain.news.value_objects import MediaType


@dataclass
class ArticleFactory:
    faker: Faker

    def create_article(
        self,
        *,
        source_url: str | None = None,
        title: str | None = None,
        author: str | None = None,
        timestamp: str | None = None,
        raw_content: str | None = None,
        quotes: list[str] | None = None,
        media: list[dict[str, str | None]] | None = None,
    ) -> Article:
        generated_source_url = source_url or self.create_article_source_url()
        generated_title = title or self.faker.sentence(nb_words=6)
        generated_author = author or self.faker.name()
        generated_timestamp = timestamp or self.faker.iso8601()
        generated_raw_content = raw_content or self.create_article_html_content()
        generated_quotes = quotes or [self.faker.sentence(nb_words=4)]
        generated_media = media or []

        article_payload = {
            "title": generated_title,
            "content": {
                "raw_content": generated_raw_content,
                "quotes": generated_quotes,
            },
            "media": generated_media,
            "timestamp": generated_timestamp,
            "author": generated_author,
            "source_url": generated_source_url,
        }
        return Article.model_validate(article_payload)

    def create_media_payload(
        self,
        *,
        media_type: MediaType,
        article_url: str | None = None,
        local_url: str | None = None,
    ) -> dict[str, str | None]:
        generated_article_url = article_url or self.faker.url()
        return {
            "media_type": media_type.value,
            "article_url": generated_article_url,
            "local_url": local_url,
        }

    def create_article_source_url(self) -> str:
        return self.faker.url()

    def create_article_html_content(self) -> str:
        paragraph = self.faker.paragraph(nb_sentences=2)
        return f"<article><p>{paragraph}</p></article>"
