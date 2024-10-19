import requests
from bs4 import BeautifulSoup
import sqlite3
from datetime import datetime
import time
import logging
import hashlib
import configparser
from pushover_integration import (
    #send_pushover_notification,
    load_pushover_config,
)

pushover_config = load_pushover_config()

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def load_config():
    config = configparser.ConfigParser()
    config.read("config.ini")
    return config


def scrape_hiddenpalace():
    url = "https://hiddenpalace.org/Main_Page"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")

    news = extract_news(soup)
    new_releases = extract_new_releases(soup)

    return news, new_releases


def create_hash(item):
    """Create a unique hash for an item based on its content"""
    hash_string = f"{item['title']}_{item['url']}_{item['date']}"
    return hashlib.md5(hash_string.encode()).hexdigest()


def extract_news(soup):
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

            news_items.append({"date": date_str, "title": title, "url": url})

    return news_items


def extract_new_releases(soup):
    new_releases = []
    releases_section = soup.find("div", class_="heading", string="Community releases")

    if releases_section:
        release_list = releases_section.find_next("div", class_="cell").find_all("li")

        for item in release_list:
            date_str = item.contents[0].strip().rstrip(":")
            title = item.find("a").text.strip()
            url = "https://hiddenpalace.org" + item.find("a")["href"]

            if item.contents[-1] is not None:
                author = (
                    item.contents[-1].text.strip()
                    if len(item.contents) > 2
                    else "Unknown"
                )
            else:
                author = "Unknown"

            new_releases.append(
                {"date": date_str, "title": title, "url": url, "author": author}
            )

    return new_releases


def update_database(news, new_releases):
    conn = sqlite3.connect("cryptkeeper.db")
    cursor = conn.cursor()

    for item in news:
        item_hash = create_hash(item)
        cursor.execute(
            """
        INSERT OR IGNORE INTO news (title, content, date, url, hash)
        VALUES (?, ?, ?, ?, ?)
        """,
            # (item["title"], item["content"], item["date"], item["url"]),
            (item["title"], None, item["date"], item["url"], item_hash),
        )

        if cursor.rowcount > 0:  # New item inserted
            pass
            # send_pushover_notification(
            #     "New Hidden Palace News",
            #     f"{item['title']}\n{item['url']}",
            #     pushover_config,
            # )

    for item in new_releases:
        item_hash = create_hash(item)
        cursor.execute(
            """
        INSERT OR IGNORE INTO new_releases (title, system, date, url, hash)
        VALUES (?, ?, ?, ?, ?)
        """,
            # (item["title"], item["system"], item["date"], item["url"]),
            (item["title"], None, item["date"], item["url"], item_hash),
        )

        if cursor.rowcount > 0:  # New item inserted
            pass
            # send_pushover_notification(
            #     "New Hidden Palace Release",
            #     f"{item['title']} by {item['author']}\n{item['url']}",
            #     pushover_config,
            # )

    conn.commit()
    conn.close()


def main():
    config = load_config()
    scrape_interval = config.getint("Scraper", "interval_hours", fallback=6)

    while True:
        logging.info("Starting scrape cycle")
        news, new_releases = scrape_hiddenpalace()
        update_database(news, new_releases)
        logging.info(f"Scrape cycle completed. Sleeping for {scrape_interval} hours")
        time.sleep(scrape_interval * 3600)  # Convert hours to seconds


if __name__ == "__main__":
    main()
