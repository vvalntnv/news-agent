from tortoise import fields, models
from tortoise.contrib.pydantic import pydantic_model_creator
from typing import List
from pydantic import BaseModel


class NewsData(models.Model):
    """
    Model to store processed news data by the agents.
    """

    id = fields.IntField(pk=True)
    summary = fields.TextField()
    fact_check_summary = fields.TextField()
    # Storing list of fact check URLs as JSON
    fact_check_urls = fields.JSONField(default=list)
    positive_opinion = fields.TextField()
    negative_opinion = fields.TextField()
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "news_data"

    def __str__(self) -> str:
        return f"Processed: {self.id}"


class NewsDataCreate(BaseModel):
    summary: str
    fact_check_summary: str
    fact_check_urls: List[str] = []
    positive_opinion: str
    negative_opinion: str


# Create Pydantic models from Tortoise models for serialization
NewsDataSchema = pydantic_model_creator(NewsData, name="NewsDataSchema")
