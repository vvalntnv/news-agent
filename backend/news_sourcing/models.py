import json
from typing import Self
from pydantic import BaseModel, ValidationError
from core.config import config


class News(BaseModel):
    title: str
    link: str


class ScrapeInformation(BaseModel):
    article_containers: list[str]
    titles_containers: list[str]
    timestamps_conteiners: list[str]
    summary_containers: list[str]
    mainArticle_container: str
    author_container: str
    author_something: str

    @classmethod
    def load_information_for_site(cls, site_name: str) -> Self:
        path = config.scrapers_info_dir / site_name

        if not path.exists():
            raise ValidationError("The file you are trying to load does not exist")

        with open(path, 'r') as file:
            data = file.read()
            data_dict = json.loads(data)

        return cls(**data_dict)
