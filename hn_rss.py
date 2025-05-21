"""
HNRSSFeedHandler: Object-oriented handler for fetching, tracking, and sending Hacker News RSS feed updates to Telegram.

- Supports jobs, best comments, and front page feeds.
- Prevents duplicate posts by tracking last sent IDs per feed.
- Sanitizes messages for Telegram HTML.
- Async methods for integration with event loops.
"""

import feedparser
import os
import re
import asyncio
from typing import Optional, List
from telegram_utils import send_telegram_message

HN_JOBS_URL = "https://hnrss.org/jobs"
HN_BEST_COMMENTS_URL = "https://hnrss.org/bestcomments"
HN_FRONT_PAGE_URL = "https://hnrss.org/frontpage"

class HNRSSFeedHandler:
    """
    Handles fetching, deduplication, and Telegram message sending for a single HN RSS feed.
    """
    def __init__(self, feed_name: str, feed_url: str, id_store_dir: Optional[str] = None):
        """
        Args:
            feed_name: Unique name for the feed (e.g. 'jobs', 'frontpage').
            feed_url: The RSS feed URL.
            id_store_dir: Directory to store last sent ID files. Defaults to current directory.
        """
        self.feed_name = feed_name
        self.feed_url = feed_url
        self.id_store_dir = id_store_dir or os.getcwd()
        self._last_id_file = os.path.join(self.id_store_dir, f"last_hn_{self.feed_name}_id.txt")

    def get_last_sent_id(self) -> Optional[str]:
        """Returns the last sent post ID for this feed, or None if not found."""
        if os.path.exists(self._last_id_file):
            with open(self._last_id_file, "r", encoding="utf-8") as f:
                return f.read().strip()
        return None

    def set_last_sent_id(self, post_id: str) -> None:
        """Updates the last sent post ID for this feed."""
        with open(self._last_id_file, "w", encoding="utf-8") as f:
            f.write(post_id)

    @staticmethod
    def sanitize_telegram_html(text: str) -> str:
        """
        Sanitizes text for Telegram HTML. Only allows supported tags and escapes others.
        Args:
            text: The input string.
        Returns:
            Sanitized string safe for Telegram HTML.
        """
        allowed_tags = ["b", "i", "a", "code", "pre", "u", "s", "tg-spoiler"]
        # Remove unsupported tags
        text = re.sub(r'<(?!/?(?:' + '|'.join(allowed_tags) + r')\b)[^>]*>', '', text)
        # Escape stray < and >
        text = text.replace('<', '&lt;').replace('>', '&gt;')
        # Unescape allowed tags
        for tag in allowed_tags:
            text = text.replace(f'&lt;{tag}&gt;', f'<{tag}>').replace(f'&lt;/{tag}&gt;', f'</{tag}>')
        return text

    def fetch_new_entries(self) -> List[dict]:
        """
        Fetches new entries from the feed since the last sent ID.
        Returns:
            List of new feedparser entries (dicts), newest last.
        """
        feed = feedparser.parse(self.feed_url)
        last_id = self.get_last_sent_id()
        new_entries = []
        for entry in feed.entries:
            if last_id and entry.id == last_id:
                break
            new_entries.append(entry)
        return list(reversed(new_entries)) if new_entries else []

    async def send_new_entries_to_telegram(self, delay_seconds: float = 2.0) -> None:
        """
        Sends new entries to Telegram, updating last sent ID and respecting rate limits.
        Args:
            delay_seconds: Delay between messages to avoid rate limits.
        """
        new_entries = self.fetch_new_entries()
        if not new_entries:
            return
        for entry in new_entries:
            message = (
                f"<b>{self.sanitize_telegram_html(entry.title)}</b>\n"
                f"<a href='{entry.link}'>Read more</a>"
            )
            send_telegram_message(message)
            await asyncio.sleep(delay_seconds)
        self.set_last_sent_id(new_entries[-1].id)

# Factory functions for each feed
def get_jobs_feed_handler(id_store_dir: Optional[str] = None) -> HNRSSFeedHandler:
    return HNRSSFeedHandler("jobs", HN_JOBS_URL, id_store_dir)

def get_bestcomments_feed_handler(id_store_dir: Optional[str] = None) -> HNRSSFeedHandler:
    return HNRSSFeedHandler("bestcomments", HN_BEST_COMMENTS_URL, id_store_dir)

def get_frontpage_feed_handler(id_store_dir: Optional[str] = None) -> HNRSSFeedHandler:
    return HNRSSFeedHandler("frontpage", HN_FRONT_PAGE_URL, id_store_dir)
