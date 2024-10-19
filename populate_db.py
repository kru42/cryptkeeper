import sqlite3


def setup_database():
    conn = sqlite3.connect("cryptkeeper.db")
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

    conn.commit()
    conn.close()


if __name__ == "__main__":
    setup_database()
