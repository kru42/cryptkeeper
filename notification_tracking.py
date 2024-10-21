import sqlite3
import logging
from datetime import datetime, timedelta
from pushover_integration import send_pushover_notification


def setup_notification_tracking():
    conn = sqlite3.connect("cryptkeeper.db")
    cursor = conn.cursor()

    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS notification_tracking (
        id INTEGER PRIMARY KEY,
        timestamp TEXT NOT NULL
    )
    """
    )

    conn.commit()
    conn.close()


def can_send_notification():
    conn = sqlite3.connect("cryptkeeper.db")
    cursor = conn.cursor()

    one_hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()

    cursor.execute(
        """
    SELECT COUNT(*) FROM notification_tracking
    WHERE timestamp > ?
    """,
        (one_hour_ago,),
    )

    count = cursor.fetchone()[0]
    conn.close()

    return count < 10


def record_notification():
    conn = sqlite3.connect("cryptkeeper.db")
    cursor = conn.cursor()

    current_time = datetime.now().isoformat()

    cursor.execute(
        """
    INSERT INTO notification_tracking (timestamp)
    VALUES (?)
    """,
        (current_time,),
    )

    conn.commit()
    conn.close()


def clean_old_notifications():
    conn = sqlite3.connect("cryptkeeper.db")
    cursor = conn.cursor()

    one_hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()

    cursor.execute(
        """
    DELETE FROM notification_tracking
    WHERE timestamp <= ?
    """,
        (one_hour_ago,),
    )

    conn.commit()
    conn.close()


def send_rate_limited_notification(title, message, pushover_config, html: int = 0):
    if can_send_notification():
        send_pushover_notification(title, message, pushover_config, html)
        record_notification()
        logging.info(f"Notification sent: {title}")
    else:
        logging.warning("Notification rate limit reached. Skipping notification.")


# Call this function at the start of your main script
setup_notification_tracking()

# Call this function periodically (e.g., at the start of each scrape cycle)
clean_old_notifications()
