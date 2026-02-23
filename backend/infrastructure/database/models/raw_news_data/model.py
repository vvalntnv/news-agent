from pydantic import BaseModel, Field
from tortoise import fields, models
from tortoise.contrib.pydantic import pydantic_model_creator


class RawNewsData(models.Model):
    """Model to store raw news data scraped from websites."""

    id = fields.IntField(primary_key=True)
    raw_text = fields.TextField()
    title = fields.CharField(max_length=512)
    url = fields.CharField(max_length=2048, null=True, unique=True)
    quotes = fields.JSONField(default=list)
    author = fields.CharField(max_length=256, default="")
    timestamp = fields.CharField(max_length=128, default="")
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:  # type: ignore
        table = "raw_news_data"

    def __str__(self) -> str:
        return self.title


class RawNewsDataCreate(BaseModel):
    raw_text: str
    title: str
    quotes: list[str] = Field(default_factory=list)


RawNewsDataSchema = pydantic_model_creator(RawNewsData, name="RawNewsDataSchema")
