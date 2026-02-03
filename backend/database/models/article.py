from tortoise import fields, models
from tortoise.contrib.pydantic import pydantic_model_creator
from pydantic import BaseModel
from typing import Optional


class Article(models.Model):
    """
    Model to store individual articles from different media sources.
    """

    id = fields.IntField(pk=True)
    media = fields.ForeignKeyField("models.Media", related_name="articles")
    article_url = fields.CharField(max_length=1024)
    news_data = fields.ForeignKeyField(
        "models.NewsData", related_name="articles", null=True
    )
    raw_data = fields.OneToOneField(
        "models.RawNewsData", related_name="article", null=True
    )
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "article"

    def __str__(self) -> str:
        return self.article_url


class ArticleCreate(BaseModel):
    media_id: int
    article_url: str
    news_data_id: Optional[int] = None
    raw_data_id: Optional[int] = None


# Create Pydantic models from Tortoise models for serialization
ArticleSchema = pydantic_model_creator(Article, name="ArticleSchema")
