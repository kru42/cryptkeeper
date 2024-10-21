import aiosqlite
from src.models import NewsItem, ReleaseItem

class DatabaseHandler:
    def __init__(self, db_name: str = "cryptkeeper.db"):
        self.db_name = db_name

    async def setup_tables(self):
        async with aiosqlite.connect(self.db_name) as db:
            cursor = await db.cursor()
            await cursor.execute(
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
            await cursor.execute(
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

    async def check_news_exists(self, item_hash: str) -> bool:
        async with aiosqlite.connect(self.db_name) as db:
            cursor = await db.cursor()
            await cursor.execute("SELECT title FROM news WHERE hash = ?", (item_hash,))
            result = await cursor.fetchone()
            return result is not None

    async def check_news_has_content(self, item_hash: str) -> bool:
        async with aiosqlite.connect(self.db_name) as db:
            cursor = await db.cursor()
            await cursor.execute(
                "SELECT content FROM news WHERE hash = ? AND content IS NOT NULL AND content != ''",
                (item_hash,),
            )
            result = await cursor.fetchone()
            return result is not None

    async def check_new_releases_exists(self, item_hash: str) -> bool:
        async with aiosqlite.connect(self.db_name) as db:
            cursor = await db.cursor()
            await cursor.execute(
                "SELECT system FROM new_releases WHERE hash = ?", (item_hash,)
            )
            result = await cursor.fetchone()
            return result is not None

    async def check_new_releases_has_system(self, item_hash: str) -> bool:
        async with aiosqlite.connect(self.db_name) as db:
            cursor = await db.cursor()
            await cursor.execute(
                # Not sure we should be checking for system != '' here
                "SELECT system FROM new_releases WHERE hash = ? AND system IS NOT NULL AND system != ''",
                (item_hash,),
            )
            result = await cursor.fetchone()
            return result is not None

    async def insert_news(self, item: NewsItem):
        async with aiosqlite.connect(self.db_name) as db:
            cursor = await db.cursor()
            await cursor.execute(
                """
            INSERT OR IGNORE INTO news (title, content, date, url, hash)
            VALUES (?, ?, ?, ?, ?)
            """,
                (
                    item.title,
                    item.content,
                    item.date,
                    item.url,
                    item.hash,
                ),
            )
            await db.commit()
            return cursor.rowcount > 0

    async def insert_release(self, item: ReleaseItem):
        async with aiosqlite.connect(self.db_name) as db:
            cursor = await db.cursor()
            await cursor.execute(
                """
            INSERT OR IGNORE INTO new_releases (title, system, date, url, author, hash)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    item.title,
                    item.system,
                    item.date,
                    item.url,
                    item.author,
                    item.hash,
                ),
            )
            await db.commit()
            return cursor.rowcount > 0

    async def update_news_content(self, item_hash: str, content: str):
        async with aiosqlite.connect(self.db_name) as db:
            cursor = await db.cursor()
            await cursor.execute(
                """
            UPDATE news
            SET content = ?
            WHERE hash = ?
            """,
                (content, item_hash),
            )
            await db.commit()

    async def update_release_system(self, item_hash: str, system: str):
        async with aiosqlite.connect(self.db_name) as db:
            cursor = await db.cursor()
            await cursor.execute(
                """
            UPDATE new_releases
            SET system = ?
            WHERE hash = ?
            """,
                (system, item_hash),
            )
            await db.commit()
