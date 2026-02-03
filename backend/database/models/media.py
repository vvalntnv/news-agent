from tortoise import fields, models
from tortoise.contrib.pydantic import pydantic_model_creator
from pydantic import BaseModel
from typing import Optional


class Media(models.Model):
    """
    Model to store media source information.
    """

    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=255, null=True)
    site_url = fields.CharField(max_length=512)
    trustworthiness = fields.FloatField(default=0.0)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "media"

    def __str__(self) -> str:
        return self.name or self.site_url


class MediaCreate(BaseModel):
    name: Optional[str] = None
    site_url: str
    trustworthiness: float = 0.0


# Create Pydantic models from Tortoise models for serialization
MediaSchema = pydantic_model_creator(Media, name="MediaSchema")
