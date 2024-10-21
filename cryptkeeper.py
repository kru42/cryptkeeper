import requests
from bs4 import BeautifulSoup
import sqlite3
from datetime import datetime
import time
import logging
import hashlib
import configparser
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from notification_tracking import (
    setup_notification_tracking,
    clean_old_notifications,
    send_rate_limited_notification,
)

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class Config:
    def __init__(self, config_file: str = "config.ini"):
        self.config = configparser.ConfigParser()
        self.config.read(config_file)

    def get_section(self, section: str) -> Dict[str, str]:
        return dict(self.config[section])

    def get(self, section: str, key: str, fallback: Any = None) -> Any:
        return self.config.get(section, key, fallback=fallback)

    def getint(self, section: str, key: str, fallback: int = None) -> int:
        return self.config.getint(section, key, fallback=fallback)


class DatabaseHandler:
    def __init__(self, db_name: str = "cryptkeeper.db"):
        self.db_name = db_name

    def connect(self):
        return sqlite3.connect(self.db_name)

    def setup_tables(self):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
            CREATE TABLE IF NOT EXISTS news (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                content TEXT,
                date TEXT NOT NULL,
                url TEXT NOT NULL,
                hash TEXT UNIQUE NOT NULL
            )
            """
            )
            cursor.execute(
                """
            CREATE TABLE IF NOT EXISTS new_releases (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                system TEXT,
                date TEXT NOT NULL,
                url TEXT NOT NULL,
                author TEXT,
                hash TEXT UNIQUE NOT NULL
            )
            """
            )

    def check_news_exists(self, item_hash: str) -> bool:
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT content FROM news WHERE hash = ?", (item_hash,))
            result = cursor.fetchone()
            return result is not None

    def check_news_has_content(self, item_hash: str) -> bool:
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                # Not sure we should be checking for content != '' here
                "SELECT content FROM news WHERE hash = ? AND content IS NOT NULL AND content != ''",
                (item_hash,),
            )
            result = cursor.fetchone()
            return result is not None

    def check_new_releases_exists(self, item_hash: str) -> bool:
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT system FROM new_releases WHERE hash = ?", (item_hash,)
            )
            result = cursor.fetchone()
            return result is not None

    def check_new_releases_has_system(self, item_hash: str) -> bool:
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                # Not sure we should be checking for system != '' here
                "SELECT system FROM new_releases WHERE hash = ? AND system IS NOT NULL AND system != ''",
                (item_hash,),
            )
            result = cursor.fetchone()
            return result is not None

    def insert_news(self, item: Dict[str, Any]):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
            INSERT OR IGNORE INTO news (title, content, date, url, hash)
            VALUES (?, ?, ?, ?, ?)
            """,
                (
                    item["title"],
                    item.get("content"),
                    item["date"],
                    item["url"],
                    item["hash"],
                ),
            )
            return cursor.rowcount > 0

    def insert_release(self, item: Dict[str, Any]):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
            INSERT OR IGNORE INTO new_releases (title, system, date, url, author, hash)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    item["title"],
                    item.get("system"),
                    item["date"],
                    item["url"],
                    item.get("author"),
                    item["hash"],
                ),
            )
            return cursor.rowcount > 0

    def update_news_content(self, item_hash: str, content: str):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
            UPDATE news
            SET content = ?
            WHERE hash = ?
            """,
                (content, item_hash),
            )

    def update_release_system(self, item_hash: str, system: str):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
            UPDATE new_releases
            SET system = ?
            WHERE hash = ?
            """,
                (system, item_hash),
            )


class NotificationManager:
    def __init__(self, pushover_config: Dict[str, str]):
        self.pushover_config = pushover_config

    def send_notification(self, title: str, message: str, html: int = 0):
        send_rate_limited_notification(title, message, self.pushover_config, html=html)


class BaseScraper(ABC):
    def __init__(
        self, db_handler: DatabaseHandler, notification_manager: NotificationManager
    ):
        self.db_handler = db_handler
        self.notification_manager = notification_manager

    @staticmethod
    def create_hash(item: Dict[str, str]) -> str:
        hash_string = f"{item['title']}_{item['url']}_{item['date']}"
        return hashlib.md5(hash_string.encode()).hexdigest()

    @abstractmethod
    def scrape(self):
        pass

    @staticmethod
    def fetch_page_content(url: str) -> BeautifulSoup:
        try:
            response = requests.get(url)
            return BeautifulSoup(response.content, "html.parser")
        except Exception as e:
            logging.error(f"Error fetching content from {url}: {str(e)}")
            return None


class HomepageScraper(BaseScraper):
    def scrape(self):
        url = "https://hiddenpalace.org/Main_Page"
        soup = self.fetch_page_content(url)
        if soup:
            news = self.extract_news(soup)
            new_releases = self.extract_new_releases(soup)
            self.update_news_and_releases(news, new_releases)

    def fetch_news_content(self, url: str) -> str:
        soup = self.fetch_page_content(url)
        if soup:
            content_div = soup.find("div", class_="mw-parser-output")
            if content_div:
                paragraphs = content_div.find_all("p")
                content = " ".join([p.get_text() for p in paragraphs])
                return content.strip()
        return "Error fetching news content"

    def fetch_release_system(self, url: str) -> str:
        soup = self.fetch_page_content(url)
        if soup:
            system_col = soup.find("td", string="System")
            if system_col:
                system = system_col.find_next_sibling("td").text.strip()
                return system if system else "Unknown"

    def extract_news(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        news_items = []
        news_section = soup.find("div", class_="heading", string="Hidden Palace news")

        if news_section:
            news_list = news_section.find_next("div", class_="cell").find_all("dd")

            for item in news_list:
                if item.find("b") is None:
                    continue
                date_str = item.find("b").text.strip().rstrip(":")
                title = item.find("a").text.strip()
                url = "https://hiddenpalace.org" + item.find("a")["href"]

                news_item = {"date": date_str, "title": title, "url": url}
                news_item["hash"] = self.create_hash(news_item)

                if not self.db_handler.check_news_exists(news_item["hash"]):
                    news_items.append(news_item)
                else:
                    logging.info(f'News item "{title}" already exists in database')

        return news_items

    def extract_new_releases(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        new_releases = []
        releases_section = soup.find(
            "div", class_="heading", string="Community releases"
        )

        if releases_section:
            release_list = releases_section.find_next("div", class_="cell").find_all(
                "li"
            )

            for item in release_list:
                date_str = item.contents[0].strip().rstrip(":")
                title = item.find("a").text.strip()
                url = "https://hiddenpalace.org" + item.find("a")["href"]
                author = (
                    item.contents[-1].text.strip()
                    if len(item.contents) > 2
                    else "Unknown"
                )

                new_release_item = {
                    "date": date_str,
                    "title": title,
                    "url": url,
                    "author": author,
                }
                new_release_item["hash"] = self.create_hash(new_release_item)

                if not self.db_handler.check_new_releases_exists(
                    new_release_item["hash"]
                ):
                    new_releases.append(new_release_item)
                else:
                    logging.info(f'Release item "{title}" already exists in database')

        return new_releases

    def update_news_and_releases(
        self, news: List[Dict[str, Any]], new_releases: List[Dict[str, Any]]
    ):
        new_news_count = 0
        new_releases_count = 0
        new_news_items = []
        new_releases_items = []

        for item in news:
            if self.db_handler.insert_news(item):
                new_news_count += 1
                new_news_items.append(item)

            if not self.db_handler.check_news_has_content(item["hash"]):
                content = self.fetch_news_content(item["url"])
                self.db_handler.update_news_content(item["hash"], content)
                logging.info(f"Content updated for {item['title']}")
                time.sleep(2)

        logging.info("News updated\nNow fetching new releases...")

        for item in new_releases:
            if self.db_handler.insert_release(item):
                new_releases_count += 1
                new_releases_items.append(item)

            if not self.db_handler.check_new_releases_has_system(item["hash"]):
                system = self.fetch_release_system(item["url"])
                self.db_handler.update_release_system(item["hash"], system)
                item["system"] = system  # XXX
                logging.info(f"System updated for {item['title']}")
                time.sleep(2)

        logging.info("New releases platform updated\nDatabase updated")

        if new_news_count > 0:
            logging.info(f"Sending notification for {new_news_count} new news items")
            message = "New Hidden Palace News:\n\n<ul>"
            for item in new_news_items:
                message += f"<li><a href='{item['url']}'>{item['title']}</a></li>"
            message += "</ul>"
            self.notification_manager.send_notification(
                f"There are {len(new_news_items)} new Hidden Palace News!",
                message,
                html=1,
            )

        if new_releases_count > 0:
            logging.info(f"Sending notification for {new_releases_count} new releases")
            message = "New Community Releases:\n\n<ul>"
            for item in new_releases_items:
                message += f"<li><a href='{item['url']}'>[{item['system']}] {item['title']}</a></li>"
            message += "</ul>"
            self.notification_manager.send_notification(
                f"There are {len(new_releases_items)} new Community Releases!",
                message,
                html=1,
            )


class CryptKeeper:
    def __init__(self, config_file: str = "config.ini"):
        self.config = Config(config_file)
        self.db_handler = DatabaseHandler()
        self.notification_manager = NotificationManager(
            self.config.get_section("Pushover")
        )
        self.homepage_scraper = HomepageScraper(
            self.db_handler, self.notification_manager
        )

    def run(self):
        self.db_handler.setup_tables()
        setup_notification_tracking()
        scrape_interval = self.config.getint("Scraper", "interval_hours", fallback=6)

        while True:
            logging.info("Starting scrape cycle")
            clean_old_notifications()
            self.homepage_scraper.scrape()
            logging.info(
                f"Scrape cycle completed. Sleeping for {scrape_interval} hours"
            )
            time.sleep(scrape_interval * 3600)  # Convert hours to seconds


if __name__ == "__main__":
    cryptkeeper = CryptKeeper()
    cryptkeeper.run()
