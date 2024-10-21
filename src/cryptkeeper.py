import asyncio
import logging
from src.config import Config
from src.database import DatabaseHandler
from src.notification.notification_manager import NotificationManager
from src.scrapers.homepage_scraper import HomepageScraper
from src.notification.notification_tracking import (
    setup_notification_tracking,
    clean_old_notifications,
)


class CryptKeeper:
    def __init__(self, config_file: str = "config.ini"):
        self.config = Config(config_file)
        self.db_handler = DatabaseHandler()
        self.notification_manager = NotificationManager(
            self.config.get_section("Pushover")
        )
        self.homepage_scraper = HomepageScraper(
            self.db_handler, self.notification_manager, self.config
        )

    async def run(self):
        await self.db_handler.setup_tables()
        await setup_notification_tracking()
        scrape_interval = self.config.getint("Scraper", "interval_hours", fallback=6)

        while True:
            logging.info("Starting scrape cycle")
            await clean_old_notifications()
            await self.homepage_scraper.scrape()
            logging.info(
                f"Scrape cycle completed. Sleeping for {scrape_interval} hours"
            )
            await asyncio.sleep(scrape_interval * 3600)
