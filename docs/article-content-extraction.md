# Article Content Extraction

## Purpose

The HTML extractor now returns structured article content through `ArticleContent`
instead of plain text. This enables reusable sanitization and downstream handling
for quote-aware processing.

## Models

### `ArticleContent`

Defined in `backend/domain/news/value_objects.py`.

- `raw_content: str`
- `quotes: list[str]`

`raw_content` stores sanitized HTML from the configured
`mainArticleContainer`. `quotes` stores extracted quote text from the same
container.

### `MediaType`

Enumerates the supported media classes: `image`, `video`, and `audio`.

### `Media`

Defined in the same module as `ArticleContent`.

- `media_type: MediaType`
- `article_url: str`
- `local_url: str | None`

Each `Media` entry holds a normalized URL that downstream agents can use to
fetch or cache the asset. `local_url` is populated when the asset is
already downloaded; otherwise it remains `None`.

### `Article`

Defined in `backend/domain/news/entities.py`.

- `content` now has type `ArticleContent`.
- `media: list[Media]` collects normalized, deduplicated media assets extracted
  from the page.

## Extraction Flow

Implemented in `backend/infrastructure/extraction/html_extractor.py`.

Sanitization is shared through `backend/infrastructure/extraction/html_sanitizer.py`
so tools and extractors can use the same rules.

1. Select `mainArticleContainer` via `ScrapeInformation.main_article_container`.
2. Clone the selected article container and sanitize it.
3. Remove irrelevant nodes:
- `script`, `style`, `noscript`, `template`
- media/embed tags (`video`, `audio`, `source`, `track`, `iframe`, `object`,
  `embed`, `canvas`, `svg`)
- tags matched by configured `imageContainers`, `videoContainers`, or
  `audioContainers` selectors (these selectors are also used later to
  discover media links outside of the main article container).
4. Extract quotes from `<blockquote>` and `<q>` tags.
5. Strip all HTML attributes except those in `attrs_to_retain`.
6. Return `ArticleContent(raw_content, quotes)`.

## Shared Sanitizer

`HtmlSanitizer.sanitize_html(...)` supports selecting a root before sanitizing:

- `root_of_analysis="head"`
- `root_of_analysis="body"`
- `root_of_analysis="article"`
- `root_of_analysis=None` (sanitize full document)

When a root is requested but not found, the sanitizer falls back to the full
document.

## Media Extraction

The extractor now gathers `Media` records independently of the sanitized
article HTML:

1. Collect `<img>`, `<video>`, and `<audio>` tags across the page. Every
   configured selector under `imageContainers`, `videoContainers`, or
   `audioContainers` is also evaluated so that linked assets (typically
   `<a>` tags) are captured.
2. Evaluate `<source>` tags and classify them by context instead of
   lumping them all together. The classification merges parent tags with the
   `type` attribute (see below) so that audio tracks inside a `<video>`
   element do not accidentally surface as video entries.
3. Normalize each discovered URL (`urljoin` + fragment stripping) and keep a
   `set` to deduplicate identical URLs coming from multiple locations.
4. Emit a `Media` record per unique URL with a matching `MediaType`.

### Source Tag Classification

- Sources that live under a `<video>` container are treated as `video`, unless
  the MIME type explicitly points to `audio/*`, in which case the extractor
  produces an `audio` entry instead. This prevents audio tracks from
  inflating the video list.
- Sources under `<audio>` are always `audio`, and those inside `<picture>` or
  `<picture>/video` structures become `image` entries.
- When no parent hints are available, the `type` MIME type is used
  directly (`video/*`, `audio/*`, `image/*`).

## Attribute Retention

`HtmlExtractor` accepts `attrs_to_retain` in the constructor:

```python
HtmlExtractor(registered_scrapers=scrapers, attrs_to_retain=("href",))
```

- Default retained attribute: `href`
- Matching is case-insensitive
- All other tag attributes are removed

## Persistence Mapping

Implemented in `backend/infrastructure/database/repositories.py`.

- `Article.content.raw_content` -> `RawNewsData.raw_text`
- `Article.content.quotes` -> `RawNewsData.quotes`
- `Article.author` -> `RawNewsData.author`
- `Article.timestamp` -> `RawNewsData.timestamp`

`RawNewsData` schema includes:

- `raw_text: TextField` (sanitized HTML)
- `quotes: JSONField` (list of extracted quotes)
- `author: CharField` (article byline persisted for downstream agents)
- `timestamp: CharField` (source timestamp/canonical publish time)
- `url: CharField` (canonical source URL used for deduplication)
