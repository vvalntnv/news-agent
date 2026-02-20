from tortoise import fields, models
from tortoise.contrib.pydantic import pydantic_model_creator
from pydantic import BaseModel
from typing import Optional


class NewsMedia(models.Model):
    """
    Model to store media source information.
    """

    id = fields.IntField(pk=True)
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


# Create Pydantic models from Tortoise models for serialization
NewsMediaSchema = pydantic_model_creator(NewsMedia, name="NewsMediaSchema")
