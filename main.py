import asyncio
import logging
from src.cryptkeeper import CryptKeeper

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


if __name__ == "__main__":
    crypt_keeper = CryptKeeper()
    asyncio.run(crypt_keeper.run())
