# Hacker News to Telegram Bot

Fetches the latest Hacker News jobs and front page posts via RSS, summarizes them using the Mistral API, and sends formatted messages (with emojis and Telegram HTML) to a Telegram channel.
You can check it out here: https://t.me/daliy_tech_hunt

## Features
- Fetches Hacker News jobs and front page posts using RSS
- Summarizes content using the Mistral API (LLM)
- Sends messages to Telegram channels using Telegram HTML (no Markdown)
- Prevents duplicate posts by tracking last sent post IDs
- Configurable delay between messages (default: 20 minutes)
- Modular, OOP, and production-ready
- Logging for all major actions and errors

## Setup
1. **Clone the repository**
2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
   (You need `feedparser`, `python-dotenv`, `aiohttp`, `requests`)
3. **Create a `.env` file** in the `app/` directory or project root with:
   ```env
   TELEGRAM_BOT_TOKEN=your-telegram-bot-token
   TELEGRAM_CHANNEL_ID=@your_channel_or_chat_id
   MISTRAL_API_KEY=your-mistral-api-key
   ```
4. **Run the bot:**
   ```bash
   python app/app.py
   ```

## Deployment
- Can be run as a cron job or on platforms like Render, Railway, etc.
- The bot will only send new posts since the last run, with a 20-minute delay between each message.

## File Structure
- `app/app.py` - Main entry point and orchestrator
- `app/hn_rss.py` - RSS feed handler (OOP)
- `app/analyze_raw_data.py` - Mistral summarizer (OOP)
- `app/telegram_utils.py` - Telegram message sender (OOP)
- `app/last_hn_*_id.txt` - Tracks last sent post IDs for each feed

## Customization
- To change the delay between messages, edit the `delay_seconds` parameter in `process_feed` in `app.py` (default: 1200 seconds = 20 minutes).
- To add more feeds, use the factory functions in `hn_rss.py` and add them to the `self.feeds` list in `HNToTelegramBot`.

## License
MIT
