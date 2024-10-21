from typing import Dict
from .notification_tracking import send_rate_limited_notification


class NotificationManager:
    def __init__(self, pushover_config: Dict[str, str]):
        self.pushover_config = pushover_config

    async def send_notification(self, title: str, message: str, html: int = 0):
        await send_rate_limited_notification(
            title, message, self.pushover_config, html=html
        )
