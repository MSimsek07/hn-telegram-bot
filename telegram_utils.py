"""
TelegramUtils: Utility class for sending messages to Telegram channels using the Bot API.
- Loads configuration from .env
- Provides static and instance methods for sending messages
- Handles Telegram HTML formatting and error handling
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

class TelegramUtils:
    """
    Utility class for sending messages to Telegram channels using the Bot API.
    """
    def __init__(self, bot_token: str = None, channel_id: str = None):
        self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.channel_id = channel_id or os.getenv("TELEGRAM_CHANNEL_ID")
        if not self.bot_token or not self.channel_id:
            raise ValueError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHANNEL_ID must be set in .env or passed explicitly.")

    def send_message(self, message: str, parse_mode: str = "HTML") -> bool:
        """
        Sends a message to the configured Telegram channel.
        Args:
            message: The message string (Telegram HTML only).
            parse_mode: Telegram parse mode (default: HTML).
        Returns:
            True if sent successfully, False otherwise.
        """
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        data = {
            "chat_id": self.channel_id,
            "text": message,
            "parse_mode": parse_mode,
            "disable_web_page_preview": False
        }
        try:
            resp = requests.post(url, data=data, timeout=10)
            resp.raise_for_status()
            return True
        except Exception as e:
            print(f"[TelegramUtils] Error sending message: {e}")
            return False

# For backward compatibility with procedural code
_default_telegram_utils = TelegramUtils()
def send_telegram_message(message: str, parse_mode: str = "HTML") -> bool:
    """
    Sends a message to the default Telegram channel using .env config.
    Args:
        message: The message string (Telegram HTML only).
        parse_mode: Telegram parse mode (default: HTML).
    Returns:
        True if sent successfully, False otherwise.
    """
    return _default_telegram_utils.send_message(message, parse_mode)
