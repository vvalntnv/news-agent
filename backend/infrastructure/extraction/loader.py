import json
from pathlib import Path
from typing import List, Tuple
from domain.news.value_objects import RSSInformation, ScrapeInformation


class NewsLoader:
    def __init__(self, sites_dir: str = "infrastructure/sites"):
        self.sites_dir = Path(sites_dir)
        if not self.sites_dir.exists():
            # Fallback for running from root
            self.sites_dir = Path("sites")
        if not self.sites_dir.exists():
            # Fallback for running from backend
            self.sites_dir = Path("../sites")

    def load_scrapers_data(
        self,
    ) -> Tuple[List[ScrapeInformation], List[RSSInformation]]:
        scrape_infos = []
        rss_infos = []

        if not self.sites_dir.exists():
            return [], []

        for file_path in self.sites_dir.glob("*.json"):
            try:
                with open(file_path, "r") as f:
                    data = json.load(f)

                # Simple heuristic: if it has 'rssFeed', it's RSS. Else Scraper.
                # Validating against models.
                if "rssFeed" in data:
                    rss_infos.append(RSSInformation(**data))
                else:
                    # Assuming it matches ScrapeInformation structure
                    # ScrapeInformation has required fields.
                    try:
                        scrape_infos.append(ScrapeInformation(**data))
                    except Exception:
                        # Might be a config file that is not a single scraper object?
                        # Or maybe validation failed.
                        pass
            except Exception as e:
                print(f"Failed to load {file_path}: {e}")

        return scrape_infos, rss_infos
