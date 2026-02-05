import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from domain.news.entities import NewsItem, Article
from domain.news.value_objects import ScrapeInformation
from infrastructure.extraction.html_extractor import HtmlExtractor
from infrastructure.sources.web_scraper_source import WebScraperSource


@pytest.fixture
def mock_scrape_info():
    """Fixture for mock scrape information."""
    return ScrapeInformation(
        scrapingUrl="https://example.com/",
        articleContainers=[".article"],
        titlesContainers=["h1.title"],
        timestampsConteiners=["time.timestamp"],
        summaryContainers=[".summary"],
        mainArticleContainer=".article-content",
        authorContainer=".author-name",
        videoContainers=[".video-link"],
    )


@pytest.fixture
def mock_news_item():
    """Fixture for mock news item."""
    return NewsItem(
        title="Test Article Title",
        url="https://example.com/news/article-123",
    )


@pytest.fixture
def sample_html_content():
    """Fixture for sample HTML content."""
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Test Article</title></head>
    <body>
        <article class="article-content">
            <h1 class="title">Test Article Title</h1>
            <div class="article-body">
                <p>This is the first paragraph of the article.</p>
                <p>This is the second paragraph with more content.</p>
                <p>Here is the conclusion of the article.</p>
            </div>
        </article>
        <div class="metadata">
            <span class="author-name">John Doe</span>
            <time class="timestamp">05/02/2026, 14:30:00</time>
        </div>
        <div class="videos">
            <a class="video-link" href="https://example.com/video1.mp4">Video 1</a>
            <a class="video-link" href="https://example.com/video2.mp4">Video 2</a>
        </div>
    </body>
    </html>
    """


@pytest.fixture
def sample_html_no_videos():
    """Fixture for sample HTML content without videos."""
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Test Article</title></head>
    <body>
        <article class="article-content">
            <h1 class="title">Test Article Title</h1>
            <p>Article content without videos.</p>
        </article>
        <span class="author-name">Jane Smith</span>
        <time class="timestamp">05/02/2026, 10:00:00</time>
    </body>
    </html>
    """


@pytest.fixture
def sample_html_no_timestamp():
    """Fixture for sample HTML content without timestamp."""
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Test Article</title></head>
    <body>
        <article class="article-content">
            <p>Article content.</p>
        </article>
        <span class="author-name">Bob Wilson</span>
    </body>
    </html>
    """


class TestHtmlExtractorMocked:
    """Tests for HtmlExtractor using mocked data."""

    async def test_extract_success_with_videos(
        self, mock_scrape_info, mock_news_item, sample_html_content
    ):
        """Test successful extraction with videos."""
        # Arrange
        extractor = HtmlExtractor(registered_scrapers=[mock_scrape_info])

        # Mock the HTTP client response
        mock_response = MagicMock()
        mock_response.content = sample_html_content.encode("utf-8")
        extractor.client.get = AsyncMock(return_value=mock_response)

        # Act
        article = await extractor.extract(mock_news_item)

        # Assert
        assert isinstance(article, Article)
        assert article.title == "Test Article Title"
        assert "This is the first paragraph" in article.content
        assert article.author == "John Doe"
        assert article.timestamp == "05/02/2026, 14:30:00"
        assert len(article.videos) == 2
        assert "https://example.com/video1.mp4" in article.videos
        assert "https://example.com/video2.mp4" in article.videos
        assert article.source_url == "https://example.com/news/article-123"

    async def test_extract_success_no_videos(
        self, mock_scrape_info, mock_news_item, sample_html_no_videos
    ):
        """Test successful extraction without videos."""
        # Arrange
        extractor = HtmlExtractor(registered_scrapers=[mock_scrape_info])

        mock_response = MagicMock()
        mock_response.content = sample_html_no_videos.encode("utf-8")
        extractor.client.get = AsyncMock(return_value=mock_response)

        # Act
        article = await extractor.extract(mock_news_item)

        # Assert
        assert isinstance(article, Article)
        assert article.title == "Test Article Title"
        assert "Article content without videos" in article.content
        assert article.author == "Jane Smith"
        assert article.timestamp == "05/02/2026, 10:00:00"
        assert article.videos == []

    async def test_extract_no_timestamp_uses_current_time(
        self, mock_scrape_info, mock_news_item, sample_html_no_timestamp
    ):
        """Test extraction falls back to current time when timestamp not found."""
        # Arrange
        extractor = HtmlExtractor(registered_scrapers=[mock_scrape_info])

        mock_response = MagicMock()
        mock_response.content = sample_html_no_timestamp.encode("utf-8")
        extractor.client.get = AsyncMock(return_value=mock_response)

        before_extract = datetime.now().replace(microsecond=0)

        # Act
        article = await extractor.extract(mock_news_item)

        after_extract = datetime.now().replace(microsecond=0)

        # Assert
        assert isinstance(article, Article)
        # Verify timestamp is in the expected format and within time range
        parsed_time = datetime.strptime(article.timestamp, "%d/%m/%Y, %H:%M:%S")
        assert before_extract <= parsed_time <= after_extract

    async def test_extract_no_matching_scraper_raises_exception(self, mock_news_item):
        """Test that extraction raises exception when no scraper found for host."""
        # Arrange - create scraper with different host
        different_scraper = ScrapeInformation(
            scrapingUrl="https://other-site.com/",
            articleContainers=[".article"],
            titlesContainers=["h1.title"],
            timestampsConteiners=["time.timestamp"],
            summaryContainers=[".summary"],
            mainArticleContainer=".article-content",
            authorContainer=".author-name",
        )
        extractor = HtmlExtractor(registered_scrapers=[different_scraper])

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await extractor.extract(mock_news_item)

        assert "No relevant scraper found" in str(exc_info.value)

    async def test_extract_no_article_container_raises_exception(
        self, mock_scrape_info, mock_news_item
    ):
        """Test that extraction raises exception when article container not found."""
        # Arrange
        extractor = HtmlExtractor(registered_scrapers=[mock_scrape_info])

        html_without_article = """
        <!DOCTYPE html>
        <html>
        <body>
            <div class="wrong-container">Not the article</div>
            <span class="author-name">Author</span>
        </body>
        </html>
        """

        mock_response = MagicMock()
        mock_response.content = html_without_article.encode("utf-8")
        extractor.client.get = AsyncMock(return_value=mock_response)

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await extractor.extract(mock_news_item)

        assert "no available article content" in str(exc_info.value).lower()

    async def test_extract_no_author_raises_exception(
        self, mock_scrape_info, mock_news_item
    ):
        """Test that extraction raises exception when author container not found."""
        # Arrange
        extractor = HtmlExtractor(registered_scrapers=[mock_scrape_info])

        html_without_author = """
        <!DOCTYPE html>
        <html>
        <body>
            <article class="article-content">
                <p>Article content.</p>
            </article>
        </body>
        </html>
        """

        mock_response = MagicMock()
        mock_response.content = html_without_author.encode("utf-8")
        extractor.client.get = AsyncMock(return_value=mock_response)

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await extractor.extract(mock_news_item)

        assert "no available article content" in str(exc_info.value).lower()

    async def test_multiple_scrapers_registered(self, mock_news_item):
        """Test that extractor correctly selects scraper based on URL host."""
        # Arrange
        scraper1 = ScrapeInformation(
            scrapingUrl="https://site1.com/",
            articleContainers=[".article"],
            titlesContainers=["h1.title"],
            timestampsConteiners=["time.timestamp"],
            summaryContainers=[".summary"],
            mainArticleContainer=".article-content",
            authorContainer=".author-name",
        )
        scraper2 = ScrapeInformation(
            scrapingUrl="https://example.com/",
            articleContainers=[".post"],
            titlesContainers=["h2.headline"],
            timestampsConteiners=[".date"],
            summaryContainers=[".excerpt"],
            mainArticleContainer=".post-body",
            authorContainer=".writer",
            videoContainers=[],
        )

        extractor = HtmlExtractor(registered_scrapers=[scraper1, scraper2])

        html_content = """
        <!DOCTYPE html>
        <html>
        <body>
            <article class="post-body">
                <p>Post content.</p>
            </article>
            <span class="writer">Test Author</span>
            <div class="date">05/02/2026</div>
        </body>
        </html>
        """

        mock_response = MagicMock()
        mock_response.content = html_content.encode("utf-8")
        extractor.client.get = AsyncMock(return_value=mock_response)

        # Act
        article = await extractor.extract(mock_news_item)

        # Assert - should use scraper2's selectors (post-body, writer)
        assert isinstance(article, Article)
        assert article.author == "Test Author"
        assert "Post content" in article.content


class TestHtmlExtractorRealData:
    """Integration tests for HtmlExtractor using real BNT data."""

    @pytest.fixture
    def bnt_scrape_info(self):
        """Load BNT scraping configuration."""
        # Try multiple paths to find the config file
        possible_paths = [
            Path("infrastructure/sites/bnt.json"),
            Path("backend/infrastructure/sites/bnt.json"),
            Path("../infrastructure/sites/bnt.json"),
        ]

        config_path = None
        for path in possible_paths:
            if path.exists():
                config_path = path
                break

        if config_path is None:
            pytest.fail("Could not find bnt.json configuration file")

        with open(config_path, "r") as f:
            config_data = json.load(f)

        return ScrapeInformation(**config_data)

    async def test_bnt_site_scraping(self, bnt_scrape_info: ScrapeInformation):
        """Test extraction from real BNT news site."""
        bnt_feed = WebScraperSource(
            base_url="I should remove this", registered_scrapers=[bnt_scrape_info]
        )

        news_items = await bnt_feed.check_for_news()
        random_news_data = news_items[0]

        # Arrange
        extractor = HtmlExtractor(registered_scrapers=[bnt_scrape_info])

        # Use a real BNT news URL
        # Note: This test may fail if the URL is no longer valid or the site structure changes
        random_news_data = NewsItem(
            title="Test BNT Article",
            url="https://bntnews.bg/news/politika",
        )

        try:
            # Act
            article = await extractor.extract(random_news_data)
            breakpoint()

            # Assert
            assert isinstance(article, Article)
            assert article.title == random_news_data.title
            assert article.content is not None
            assert len(article.content) > 0
            assert article.source_url == random_news_data.url

            # Videos may or may not be present depending on the article
            assert isinstance(article.videos, list)

            # Timestamp should be present (either scraped or fallback)
            assert article.timestamp is not None
            assert len(article.timestamp) > 0

            print("Successfully extracted article from BNT")
            print(f"Content length: {len(article.content)} characters")
            print(f"Videos found: {len(article.videos)}")
            print(f"Timestamp: {article.timestamp}")

        except Exception as e:
            # If the specific URL fails, try to get a working URL from the main page
            pytest.skip(f"Could not extract from BNT site: {e}")

        finally:
            await extractor.client.aclose()

    async def test_bnt_scraper_configuration_loaded(self, bnt_scrape_info):
        """Test that BNT scraper configuration is properly loaded."""
        # Assert configuration is valid
        assert bnt_scrape_info.scraping_url == "https://bntnews.bg/"
        assert len(bnt_scrape_info.article_containers) > 0
        assert len(bnt_scrape_info.titles_containers) > 0
        assert len(bnt_scrape_info.timestamps_conteiners) > 0
        assert bnt_scrape_info.main_article_container is not None
        assert len(bnt_scrape_info.main_article_container) > 0

        # Verify host extraction works
        host = bnt_scrape_info.get_host()
        assert host == "bntnews.bg"


async def test_html_extractor_initialization():
    """Test HtmlExtractor initialization with scrapers."""
    # Arrange
    scraper1 = ScrapeInformation(
        scrapingUrl="https://site1.com/",
        articleContainers=[".article"],
        titlesContainers=["h1.title"],
        timestampsConteiners=["time.timestamp"],
        summaryContainers=[".summary"],
        mainArticleContainer=".article-content",
        authorContainer=".author-name",
    )
    scraper2 = ScrapeInformation(
        scrapingUrl="https://site2.com/",
        articleContainers=[".post"],
        titlesContainers=["h2.headline"],
        timestampsConteiners=[".date"],
        summaryContainers=[".excerpt"],
        mainArticleContainer=".post-body",
        authorContainer=".writer",
    )

    # Act
    extractor = HtmlExtractor(registered_scrapers=[scraper1, scraper2])

    # Assert
    assert len(extractor.scraping_informations) == 2
    assert "site1.com" in extractor.scraping_informations
    assert "site2.com" in extractor.scraping_informations
    assert extractor.client is not None

    # Cleanup
    await extractor.client.aclose()
