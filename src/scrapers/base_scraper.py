from abc import ABC, abstractmethod
import aiohttp
from bs4 import BeautifulSoup
import logging
from src.config import Config
from src.database import DatabaseHandler
from src.notification.notification_manager import NotificationManager


class BaseScraper(ABC):
    def __init__(
        self,
        db_handler: DatabaseHandler,
        notification_manager: NotificationManager,
        config: Config,
    ):
        self.db_handler = db_handler
        self.notification_manager = notification_manager
        self.config = config
        self.session = None

    async def get_session(self):
        if self.session is None:
            self.session = aiohttp.ClientSession()
        return self.session

    async def close_session(self):
        if self.session is not None:
            await self.session.close()
            self.session = None

    async def fetch_page_content(self, url: str) -> BeautifulSoup:
        session = await self.get_session()
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    logging.error(
                        f"Failed to fetch page content from {url}. Status code: {response.status}"
                    )
                    return None
        except aiohttp.ClientError as e:
            logging.error(f"Error fetching page content from {url}: {e}")
            return None

    @abstractmethod
    async def scrape(self):
        pass

    async def close(self):
        await self.close_session()
