from typing import List
from domain.news.protocols import NewsSource, ContentExtractor, ArticleRepository


class ETLManager:
    """
    Coordinates the ETL process: Source -> Extractor -> Repository.
    """

    def __init__(
        self,
        sources: List[NewsSource],
        extractor: ContentExtractor,
        repository: ArticleRepository,
    ):
        self.sources = sources
        self.extractor = extractor
        self.repository = repository

    async def run(self):
        """
        Runs the ETL pipeline for all sources.
        """
        for source in self.sources:
            try:
                # 1. Fetch News Items (Links)
                items = await source.check_for_news()

                for item in items:
                    # 2. Check if already exists (Optimization)
                    existing = await self.repository.get_by_url(item.url)
                    if existing:
                        continue

                    # 3. Extract Content
                    try:
                        article = await self.extractor.extract(item)

                        # 4. Save to Repository
                        await self.repository.save(article)
                    except NotImplementedError:
                        # Skip extraction if not implemented (for now)
                        print(f"Extraction not implemented for {item.url}")
                    except Exception as e:
                        print(f"Error processing {item.url}: {e}")

            except Exception as source_error:
                print(f"Error collecting from source: {source_error}")
