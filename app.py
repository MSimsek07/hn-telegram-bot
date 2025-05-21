"""
HN to Telegram Bot
-----------------
Fetches the latest Hacker News jobs and front page posts, summarizes them using Mistral, and sends the results to a Telegram channel.

Main class: HNToTelegramBot
- process_feed: Fetches, summarizes, and sends each post.
- run: Runs the bot for jobs and front page feeds.

Entry point: main()
"""

import asyncio
from dotenv import load_dotenv
from hn_rss import get_jobs_feed_handler, get_frontpage_feed_handler
from analyze_raw_data import MistralSummarizer
from telegram_utils import TelegramUtils
import logging

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

class HNToTelegramBot:
    """
    Main orchestrator for fetching HN RSS, summarizing, and sending to Telegram.
    """
    def __init__(self, telegram_utils: TelegramUtils = None, summarizer: MistralSummarizer = None):
        self.telegram_utils = telegram_utils or TelegramUtils()
        self.summarizer = summarizer or MistralSummarizer()
        self.feeds = [
            get_jobs_feed_handler(),
            get_frontpage_feed_handler(),
        ]

    async def process_feed(self, feed_handler, delay_seconds: float = 1200.0):
        """
        Fetches entries from the given feed, summarizes with Mistral, and sends to Telegram.
        Args:
            feed_handler: The feed handler instance.
            delay_seconds (float): Delay between sending messages (seconds).
        """
        new_entries = feed_handler.fetch_new_entries()
        if not new_entries:
            logging.info(f"No new entries for feed: {feed_handler.feed_name}")
            return
        for idx, entry in enumerate(new_entries):
            try:
                # Summarize content
                summary = await self.summarizer.summarize(entry.title + "\n" + getattr(entry, "summary", ""))
                message = (
                    f"<b>{feed_handler.sanitize_telegram_html(entry.title)}</b>\n"
                    f"<a href='{entry.link}'>Read more</a>\n\n"
                    f"{feed_handler.sanitize_telegram_html(summary) if summary else ''}"
                )
                sent = self.telegram_utils.send_message(message)
                if sent:
                    logging.info(f"Sent message for: {entry.title}")
                else:
                    logging.error(f"Failed to send message for: {entry.title}")
            except Exception as e:
                logging.error(f"Error processing entry '{entry.title}': {e}")
            if idx < len(new_entries) - 1:
                logging.info(f"Waiting {delay_seconds/60:.1f} minutes before next message...")
                await asyncio.sleep(delay_seconds)
        feed_handler.set_last_sent_id(new_entries[-1].id)
        logging.info(f"Updated last sent ID for feed: {feed_handler.feed_name}")

    async def run(self):
        """
        Run the bot: process jobs and front page feeds.
        """
        for feed in self.feeds:
            await self.process_feed(feed)


# For backward compatibility with procedural code
def main():
    """
    Entrypoint for running the HN to Telegram bot.
    """
    load_dotenv()
    bot = HNToTelegramBot()
    asyncio.run(bot.run())

if __name__ == "__main__":
    main()