import configparser
import logging
import aiohttp


def load_pushover_config():
    config = configparser.ConfigParser()
    config.read("config.ini")
    return {
        "user_key": config["Pushover"]["user_key"],
        "api_token": config["Pushover"]["api_token"],
    }


async def send_pushover_notification(title, message, config, html: int = 0):
    url = "https://api.pushover.net/1/messages.json"
    data = {
        "token": config["api_token"],
        "user": config["user_key"],
        "title": title,
        "message": message,
        "html": html,
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, data=data) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as e:
            logging.error(f"Error sending Pushover notification: {str(e)}")
            return False
