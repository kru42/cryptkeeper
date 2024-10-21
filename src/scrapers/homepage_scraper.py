import asyncio
import hashlib
from bs4 import BeautifulSoup
import logging
from typing import List, Dict
from src.models import NewsItem, ReleaseItem
from .base_scraper import BaseScraper


class HomepageScraper(BaseScraper):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.semaphore = asyncio.Semaphore(5)  # Limit to 5 concurrent requests

    @staticmethod
    def create_hash(item: Dict[str, str]) -> str:
        hash_string = f"{item['title']}_{item['url']}_{item['date']}"
        return hashlib.md5(hash_string.encode()).hexdigest()

    async def scrape(self):
        url = self.config.get("Scraper", "homepage_url")
        content = await self.fetch_page_content(url)
        if content:
            soup = BeautifulSoup(content, "html.parser")
            news = await self.extract_news(soup)
            new_releases = await self.extract_new_releases(soup)
            await self.update_news_and_releases(news, new_releases)
        await self.close_session()

    async def fetch_news_content(self, url: str) -> str:
        session = await self.get_session()
        async with session.get(url) as response:
            if response.status == 200:
                content = await response.text()
                soup = BeautifulSoup(content, "html.parser")
                content_div = soup.find("div", class_="mw-parser-output")
                if content_div:
                    paragraphs = content_div.find_all("p")
                    return "\n".join([p.text for p in paragraphs])
            return "Error fetching news content"

    async def fetch_release_system(self, url: str) -> str:
        session = await self.get_session()
        async with session.get(url) as response:
            if response.status == 200:
                content = await response.text()
                soup = BeautifulSoup(content, "html.parser")
                system_col = soup.find("td", string="System")
                if system_col:
                    system = system_col.find_next_sibling("td").text.strip()
                    return system if system else "Unknown"
            return "Unknown"

    async def extract_news(self, soup: BeautifulSoup) -> List[NewsItem]:
        news_items: List[NewsItem] = []
        news_section = soup.find("div", class_="heading", string="Hidden Palace news")

        if news_section:
            news_list = news_section.find_next("div", class_="cell").find_all("dd")

            for item in news_list:
                if item.find("b") is None:
                    continue
                date_str = item.find("b").text.strip().rstrip(":")
                title = item.find("a").text.strip()
                url = self.config.get("Scraper", "base_url") + item.find("a")["href"]

                news_item: NewsItem = NewsItem(date=date_str, title=title, url=url)
                news_item.hash = self.create_hash(news_item.__dict__)

                if not await self.db_handler.check_news_exists(
                    news_item.hash
                ) or not await self.db_handler.check_news_has_content(news_item.hash):
                    news_items.append(news_item)
                else:
                    logging.info(f'News item "{title}" already exists in database')

        return news_items

    async def extract_new_releases(self, soup: BeautifulSoup) -> List[ReleaseItem]:
        new_releases: List[ReleaseItem] = []
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
                url = self.config.get("Scraper", "base_url") + item.find("a")["href"]
                author = (
                    item.contents[-1].text.strip()
                    if len(item.contents) > 2
                    else "Unknown"
                )

                new_release_item: ReleaseItem = ReleaseItem(
                    date=date_str, title=title, url=url, author=author
                )
                new_release_item.hash = self.create_hash(new_release_item.__dict__)

                if not await self.db_handler.check_new_releases_exists(
                    new_release_item.hash
                ) or not await self.db_handler.check_new_releases_has_system(
                    new_release_item.hash
                ):
                    new_releases.append(new_release_item)
                else:
                    logging.info(f'Release item "{title}" already exists in database')

        return new_releases

    async def update_news_and_releases(
        self, news: List[NewsItem], new_releases: List[ReleaseItem]
    ):
        new_news_items = []
        new_releases_items = []

        async def process_news_item(item: NewsItem):
            async with self.semaphore:
                if await self.db_handler.insert_news(item):
                    new_news_items.append(item)

                if not await self.db_handler.check_news_has_content(item.hash):
                    content = await self.fetch_news_content(item.url)
                    await self.db_handler.update_news_content(item.hash, content)
                    logging.info(f"Content updated for {item.title}")

                await asyncio.sleep(5)

        async def process_release_item(item: ReleaseItem):
            async with self.semaphore:
                if await self.db_handler.insert_release(item):
                    new_releases_items.append(item)

                if not await self.db_handler.check_new_releases_has_system(item.hash):
                    system = await self.fetch_release_system(item.url)
                    await self.db_handler.update_release_system(item.hash, system)
                    item.system = system
                    logging.info(f"System updated for {item.title}")
                await asyncio.sleep(5)

        await asyncio.gather(
            *[process_news_item(item) for item in news],
            *[process_release_item(item) for item in new_releases],
        )

        logging.info("News and releases updated")

        if new_news_items:
            await self.send_news_notification(new_news_items)
        if new_releases_items:
            await self.send_releases_notification(new_releases_items)

    async def send_news_notification(self, new_news_items: List[NewsItem]):
        logging.info(f"Sending notification for {len(new_news_items)} new news items")
        message = "New Hidden Palace News:\n\n<ul>"
        for item in new_news_items:
            message += f"<li><a href='{item.url}'>{item.title}</a></li>"
        message += "</ul>"
        await self.notification_manager.send_notification(
            f"There are {len(new_news_items)} new Hidden Palace News!",
            message,
            html=1,
        )

    async def send_releases_notification(self, new_releases_items: List[ReleaseItem]):
        logging.info(f"Sending notification for {len(new_releases_items)} new releases")
        message = "New Community Releases:\n\n<ul>"
        for item in new_releases_items:
            message += f"<li><a href='{item.url}'>[{item.system}] {item.title}</a></li>"
        message += "</ul>"
        await self.notification_manager.send_notification(
            f"There are {len(new_releases_items)} new Community Releases!",
            message,
            html=1,
        )
