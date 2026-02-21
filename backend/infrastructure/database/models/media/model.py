from typing import Optional

from pydantic import BaseModel
from tortoise import fields, models
from tortoise.contrib.pydantic import pydantic_model_creator


class NewsMedia(models.Model):
    """Model to store media source information."""

    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=255, null=True)
    site_url = fields.CharField(max_length=512, unique=True, db_index=True)
    trustworthiness = fields.FloatField(default=0.0)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:  # type: ignore
        table = "news_media"

    def __str__(self) -> str:
        return self.name or self.site_url


class NewsMediaCreate(BaseModel):
    name: Optional[str] = None
    site_url: str
    trustworthiness: float = 0.0


NewsMediaSchema = pydantic_model_creator(NewsMedia, name="NewsMediaSchema")


class ArticleMedia(models.Model):
    """Persistent metadata for a specific article's media asset."""

    id = fields.IntField(primary_key=True)
    article = fields.ForeignKeyField(
        "models.Article",
        related_name="media_items",
        on_delete=fields.CASCADE,
    )
    media_type = fields.CharField(max_length=64)
    article_url = fields.CharField(max_length=2048)
    local_url = fields.CharField(max_length=2048, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:  # type: ignore[override]
        table = "media"


class ArticleMediaCreate(BaseModel):
    media_type: str
    article_url: str
    local_url: Optional[str] = None


ArticleMediaSchema = pydantic_model_creator(ArticleMedia, name="ArticleMediaSchema")
