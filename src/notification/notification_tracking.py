import aiosqlite
import logging
from datetime import datetime, timedelta
from src.notification.pushover_integration import send_pushover_notification


async def setup_notification_tracking():
    async with aiosqlite.connect("cryptkeeper.db") as db:
        await db.execute(
            """
        CREATE TABLE IF NOT EXISTS notification_tracking (
            id INTEGER PRIMARY KEY,
            timestamp TEXT NOT NULL
        )
        """
        )
        await db.commit()


async def can_send_notification():
    async with aiosqlite.connect("cryptkeeper.db") as db:
        one_hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()

        async with db.execute(
            """
        SELECT COUNT(*) FROM notification_tracking
        WHERE timestamp > ?
        """,
            (one_hour_ago,),
        ) as cursor:
            count = await cursor.fetchone()

        return count[0] < 10


async def record_notification():
    async with aiosqlite.connect("cryptkeeper.db") as db:
        current_time = datetime.now().isoformat()

        await db.execute(
            """
        INSERT INTO notification_tracking (timestamp)
        VALUES (?)
        """,
            (current_time,),
        )

        await db.commit()


async def clean_old_notifications():
    async with aiosqlite.connect("cryptkeeper.db") as db:
        one_hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()

        await db.execute(
            """
        DELETE FROM notification_tracking
        WHERE timestamp <= ?
        """,
            (one_hour_ago,),
        )

        await db.commit()


async def send_rate_limited_notification(
    title, message, pushover_config, html: int = 0
):
    if await can_send_notification():
        success = await send_pushover_notification(
            title, message, pushover_config, html
        )
        if success:
            await record_notification()
            logging.info(f"Notification sent: {title}")

        else:
            logging.error(f"Failed to send notification: {title}")
    else:
        logging.warning("Notification rate limit reached. Skipping notification.")
