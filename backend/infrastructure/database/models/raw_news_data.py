from tortoise import fields, models
from tortoise.contrib.pydantic import pydantic_model_creator
from pydantic import BaseModel, Field


class RawNewsData(models.Model):
    """
    Model to store raw news data scraped from websites.
    """

    id = fields.IntField(pk=True)
    raw_text = fields.TextField()
    title = fields.CharField(max_length=512)
    url = fields.CharField(max_length=2048, null=True, unique=True)
    # Storing list of video URLs as JSON
    videos = fields.JSONField(default=list)
    # Storing list of extracted quotes as JSON
    quotes = fields.JSONField(default=list)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "raw_news_data"

    def __str__(self) -> str:
        return self.title


class RawNewsDataCreate(BaseModel):
    raw_text: str
    title: str
    videos: list[str] = Field(default_factory=list)
    quotes: list[str] = Field(default_factory=list)


# Create Pydantic models from Tortoise models for serialization
RawNewsDataSchema = pydantic_model_creator(RawNewsData, name="RawNewsDataSchema")
