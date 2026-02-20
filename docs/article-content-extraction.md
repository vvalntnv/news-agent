# Article Content Extraction

## Purpose

The HTML extractor now returns structured article content through `ArticleContent`
instead of plain text. This enables reusable sanitization and downstream handling
for quote-aware processing.

## Models

### `ArticleContent`

Defined in `/Users/vvalntnv/.codex/worktrees/31d3/news-agent/backend/domain/news/value_objects.py`.

- `raw_content: str`
- `quotes: list[str]`

`raw_content` stores sanitized HTML from the configured
`mainArticleContainer`. `quotes` stores extracted quote text from the same
container.

### `Article`

Defined in `/Users/vvalntnv/.codex/worktrees/31d3/news-agent/backend/domain/news/entities.py`.

- `content` now has type `ArticleContent`.

## Extraction Flow

Implemented in
`/Users/vvalntnv/.codex/worktrees/31d3/news-agent/backend/infrastructure/extraction/html_extractor.py`.

1. Select `mainArticleContainer` via `ScrapeInformation.main_article_container`.
2. Clone the selected article container and sanitize it.
3. Remove irrelevant nodes:
- `script`, `style`, `noscript`, `template`
- media/embed tags (`video`, `audio`, `source`, `track`, `iframe`, `object`,
  `embed`, `canvas`, `svg`)
- tags matched by configured `video_containers` selectors
4. Extract quotes from `<blockquote>` and `<q>` tags.
5. Strip all HTML attributes except those in `attrs_to_retain`.
6. Return `ArticleContent(raw_content, quotes)`.

## Attribute Retention

`HtmlExtractor` accepts `attrs_to_retain` in the constructor:

```python
HtmlExtractor(registered_scrapers=scrapers, attrs_to_retain=("href",))
```

- Default retained attribute: `href`
- Matching is case-insensitive
- All other tag attributes are removed

## Persistence Mapping

Implemented in
`/Users/vvalntnv/.codex/worktrees/31d3/news-agent/backend/infrastructure/database/repositories.py`.

- `Article.content.raw_content` -> `RawNewsData.raw_text`
- `Article.content.quotes` -> `RawNewsData.quotes`

`RawNewsData` schema includes:

- `raw_text: TextField` (sanitized HTML)
- `quotes: JSONField` (list of extracted quotes)
- `videos: JSONField`
