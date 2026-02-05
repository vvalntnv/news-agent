from domain.news.entities import NewsItem, Article
from domain.news.protocols import ContentExtractor


class HtmlExtractor(ContentExtractor):
    """
    Extracts content from HTML pages.
    """

    async def extract(self, item: NewsItem) -> Article:
        # TODO: Implement extraction logic
        raise NotImplementedError("Extraction logic not yet implemented")
