# Database Repositories

## Purpose

The repository layer now follows a shared contract so every database repository
uses the same core methods and naming.

## Base Contract

Defined in `backend/domain/common/repositories/protocols.py` as
`RepositoryProtocol`:

- `create(payload)`
- `create_many(payloads)`
- `update_one(filters, payload)`
- `update_many(filters, payload)`
- `get(filters)`
- `get_many(filters, limit, offset, order_by)`

The contract is generic and strongly typed with Pydantic models so repository
inputs and outputs stay explicit.

## Article Contract

Defined under news-specific domain modules:

- `backend/domain/news/repositories/protocols.py` defines
  `ArticleRepositoryProtocol` and extends `RepositoryProtocol`
- `backend/domain/news/repository_models/article.py` defines
  `ArticleRepositoryFilters` query filters (`article_id`, `article_url`)
- `backend/domain/news/repository_models/article.py` defines
  `ArticleRepositoryUpdatePayload` for partial updates
- Extra article-specific methods:
  - `get_by_url(url)`
  - `exists_by_url(url)`
  - `update_media_local_url(article_url, source_url, local_url)`

## Repository Placement

Repositories are colocated with their model modules.

Example:

- Model: `backend/infrastructure/database/models/article/model.py`
- Repository: `backend/infrastructure/database/models/article/repository.py`

This keeps model persistence logic and ORM model definitions within the same
semantic module.

## Mapping Flow

Article repository mappers now live under:

- `backend/infrastructure/database/models/article/mappers/article_mapper.py`
- `backend/infrastructure/database/models/article/mappers/media_mapper.py`

These files contain only mapping logic between ORM rows and domain models.
