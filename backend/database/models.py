from tortoise import fields, models
from tortoise.contrib.pydantic import pydantic_model_creator
from typing import List, Optional
from pydantic import BaseModel


class RawNewsData(models.Model):
    """
    Model to store raw news data scraped from websites.
    """
    id = fields.IntField(pk=True)
    raw_text = fields.TextField()
    title = fields.CharField(max_length=512)
    # Storing list of video URLs as JSON
    videos = fields.JSONField(default=list) 
    created_at = fields.DatetimeField(auto_now_add=True)
    
    class Meta:
        table = "raw_news_data"

    def __str__(self) -> str:
        return self.title


class NewsData(models.Model):
    """
    Model to store processed news data by the agents.
    """
    id = fields.IntField(pk=True)
    raw_news_data = fields.ForeignKeyField('models.RawNewsData', related_name='processed_data')
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
        return f"Processed: {self.raw_news_data_id}" 


# Pydantic Models for Data Validation (Create & Response)

class RawNewsDataCreate(BaseModel):
    raw_text: str
    title: str
    videos: List[str] = []

class NewsDataCreate(BaseModel):
    raw_news_data_id: int
    summary: str
    fact_check_summary: str
    fact_check_urls: List[str] = []
    positive_opinion: str
    negative_opinion: str

# Create Pydantic models from Tortoise models for serialization
RawNewsDataSchema = pydantic_model_creator(RawNewsData, name="RawNewsDataSchema")
NewsDataSchema = pydantic_model_creator(NewsData, name="NewsDataSchema")
