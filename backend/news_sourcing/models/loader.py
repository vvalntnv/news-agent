import json
import os
from pathlib import Path

from pydantic import ValidationError
from core.config import config
from .models import ScrapeInformation, RSSInformation

type FeedInfo = ScrapeInformation | RSSInformation
type IsRSSFeed = bool


class NewsLoader:
    def __init__(
        self,
        base_folder: Path = config.scrapers_info_dir,
    ) -> None:
        self.base_folder = base_folder

    def load_scrapers_data(
        self,
    ) -> tuple[list[ScrapeInformation], list[RSSInformation]]:
        if not self.base_folder.is_dir():
            raise ValidationError("The base folder is not a dir")

        scraper_files = os.listdir(self.base_folder)

        output = {"scrapers": [], "rss_feeds": []}

        for file in scraper_files:
            file_wrapped = Path(file)

            if file_wrapped.is_dir():
                raise ValidationError("The file: " + file + " is a directory")

            with open(file_wrapped, "r") as file:
                data = file.read()
                info, is_rss_feed = self._make_model_using_data(data)

            if is_rss_feed:
                output["rss_feeds"].append(info)
            else:
                output["scrapers"].append(info)

        return (output["scrapers"], output["rss_feeds"])

    def _make_model_using_data(
        self,
        data: str | bytes | bytearray,
    ) -> tuple[FeedInfo, IsRSSFeed]:
        deserialized_data = json.loads(data)

        assert isinstance(
            deserialized_data, dict
        ), "deserialized data is invalid format"

        if "rss_feed" in deserialized_data:
            model = RSSInformation(**deserialized_data)
            return model, True

        model = ScrapeInformation(**deserialized_data)
        return model, False
