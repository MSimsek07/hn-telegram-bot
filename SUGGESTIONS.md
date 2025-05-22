# HN Telegram Bot: Improvement Suggestions

This document outlines suggested improvements and new features for the HN Telegram Bot.

## 1. Activate the "Best Comments" Feed

The bot already has most of the underlying functionality to support fetching and processing Hacker News "Best Comments." Here's how to activate it:

**File: `hn_rss.py`**

No changes are strictly needed in `hn_rss.py` as it already includes:
- `HN_BEST_COMMENTS_URL = "https://hnrss.org/bestcomments"`
- `def get_bestcomments_feed_handler(...)`: A factory function to create a handler for this feed.

The `HNRSSFeedHandler` will automatically use a file named `last_hn_bestcomments_id.txt` to keep track of sent comments.

**File: `app.py`**

Two changes are needed:

1.  **Import the handler:**
    Add `get_bestcomments_feed_handler` to the existing imports from `hn_rss`:

    ```python
    # Before:
    # from hn_rss import get_jobs_feed_handler, get_frontpage_feed_handler

    # After:
    from hn_rss import get_jobs_feed_handler, get_frontpage_feed_handler, get_bestcomments_feed_handler
    ```

2.  **Add the feed to the bot's feed list:**
    In the `HNToTelegramBot` class, modify the `__init__` method to include the "best comments" feed handler:

    ```python
    # Before:
    # self.feeds = [
    #     get_jobs_feed_handler(),
    #     get_frontpage_feed_handler(),
    # ]

    # After:
    self.feeds = [
        get_jobs_feed_handler(),
        get_frontpage_feed_handler(),
        get_bestcomments_feed_handler(), # Add this line
    ]
    ```

With these changes, the bot will start fetching, summarizing, and sending new entries from the Hacker News "Best Comments" RSS feed in addition to the "Jobs" and "Front Page" feeds.

---

## 2. Make Message Delay Configurable

The delay between sending multiple messages from the *same* feed is currently hardcoded. Making this configurable via an environment variable provides more flexibility.

**File: `app.py`**

1.  **Import `os`:**
    Add `import os` at the top of the file if it's not already there.

    ```python
    import asyncio
    import os # Add this line
    from dotenv import load_dotenv
    # ... other imports
    ```

2.  **Read Environment Variable in `HNToTelegramBot.__init__`:**
    In the `HNToTelegramBot` class, modify the `__init__` method to read the `MESSAGE_DELAY_SECONDS` environment variable. Provide a default value if it's not set.

    ```python
    class HNToTelegramBot:
        def __init__(self, telegram_utils: TelegramUtils = None, summarizer: MistralSummarizer = None):
            self.telegram_utils = telegram_utils or TelegramUtils()
            self.summarizer = summarizer or MistralSummarizer()
            self.feeds = [
                get_jobs_feed_handler(),
                get_frontpage_feed_handler(),
                # get_bestcomments_feed_handler(), # Assuming this was added from step 1
            ]
            # Add these lines:
            try:
                self.message_delay_seconds = float(os.getenv("MESSAGE_DELAY_SECONDS", "1200.0"))
            except ValueError:
                logging.warning(f"Invalid value for MESSAGE_DELAY_SECONDS. Using default 1200.0 seconds.")
                self.message_delay_seconds = 1200.0
    ```

3.  **Use the Configured Delay in `process_feed`:**
    Modify the `process_feed` method. Option A is generally preferred for maintaining flexibility.

    **Option A (Pass as argument - Recommended):**
    Change the `process_feed` signature and how `delay_seconds` is determined:
    ```python
    async def process_feed(self, feed_handler, delay_seconds: float = None): # Remove default here
        """
        Fetches entries from the given feed, summarizes with Mistral, and sends to Telegram.
        Args:
            feed_handler: The feed handler instance.
            delay_seconds (float): Delay between sending messages (seconds). If None, uses instance default.
        """
        current_delay = delay_seconds if delay_seconds is not None else self.message_delay_seconds

        new_entries = feed_handler.fetch_new_entries()
        if not new_entries:
            logging.info(f"No new entries for feed: {feed_handler.feed_name}")
            return
        for idx, entry in enumerate(new_entries):
            # ... (message sending logic) ...
            if idx < len(new_entries) - 1:
                logging.info(f"Waiting {current_delay/60:.1f} minutes before next message...")
                await asyncio.sleep(current_delay) # Use current_delay
        # ... (rest of the method)
    ```
    Then, in the `run` method, explicitly pass `self.message_delay_seconds`:
    ```python
    async def run(self):
        """
        Run the bot: process jobs and front page feeds.
        """
        for feed in self.feeds:
            # Pass the configured delay to process_feed
            await self.process_feed(feed, delay_seconds=self.message_delay_seconds)
    ```

    **Option B (Directly use instance variable):**
    Alternatively, if `process_feed`'s delay is always the global one:
    ```python
    async def process_feed(self, feed_handler): # Remove delay_seconds from parameters
        # ...
        # Directly use self.message_delay_seconds for asyncio.sleep()
            if idx < len(new_entries) - 1:
                logging.info(f"Waiting {self.message_delay_seconds/60:.1f} minutes before next message...")
                await asyncio.sleep(self.message_delay_seconds) # Use self.message_delay_seconds
        # ...
    ```
    And the call in `run` becomes:
    ```python
    async def run(self):
        for feed in self.feeds:
            await self.process_feed(feed) # No delay parameter passed
    ```

**To Use:**

Set the `MESSAGE_DELAY_SECONDS` environment variable to the desired number of seconds (e.g., `MESSAGE_DELAY_SECONDS=300` for 5 minutes). If not set, it will default to 1200 seconds (20 minutes), or whatever default you set in `os.getenv`.

---

## 3. Improve Error Handling for Sending Messages

To make message sending more resilient to transient network issues or Telegram API hiccups (like rate limiting), implement a retry mechanism with exponential backoff in `TelegramUtils`.

**File: `telegram_utils.py`**

1.  **Import `time` and `requests.exceptions`:**
    Add these imports at the top of the file:

    ```python
    import os
    import requests
    from requests.exceptions import RequestException, HTTPError # Add HTTPError
    import time # Add this line
    from dotenv import load_dotenv
    ```

2.  **Modify `send_message` method:**
    Update the `send_message` method in the `TelegramUtils` class to include the retry logic.

    ```python
    class TelegramUtils:
        def __init__(self, bot_token: str = None, channel_id: str = None):
            self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
            self.channel_id = channel_id or os.getenv("TELEGRAM_CHANNEL_ID")
            if not self.bot_token or not self.channel_id:
                raise ValueError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHANNEL_ID must be set in .env or passed explicitly.")

        def send_message(self, message: str, parse_mode: str = "HTML", max_retries: int = 3, initial_backoff: float = 1.0) -> bool:
            """
            Sends a message to the configured Telegram channel with retries on failure.
            Args:
                message: The message string (Telegram HTML only).
                parse_mode: Telegram parse mode (default: HTML).
                max_retries: Maximum number of retries.
                initial_backoff: Initial delay in seconds for backoff.
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
            
            current_retry = 0
            backoff_seconds = initial_backoff
            
            while current_retry <= max_retries:
                try:
                    resp = requests.post(url, data=data, timeout=10) # Timeout for the request
                    resp.raise_for_status()  # Raises HTTPError for 4xx/5xx responses
                    return True
                except HTTPError as e:
                    # Retry on 429 (Too Many Requests) or 5xx server errors
                    if e.response.status_code == 429 or e.response.status_code >= 500:
                        logging.warning(f"[TelegramUtils] HTTPError {e.response.status_code} sending message. Retrying in {backoff_seconds}s... (Attempt {current_retry+1}/{max_retries+1})")
                    else:
                        # For other HTTP errors (e.g., 400, 401, 403), don't retry, just log and fail.
                        logging.error(f"[TelegramUtils] HTTPError {e.response.status_code} sending message: {e}. Not retrying.")
                        return False 
                except RequestException as e:
                    # Catch other network-related errors (ConnectionError, Timeout, etc.)
                    logging.warning(f"[TelegramUtils] RequestException sending message: {e}. Retrying in {backoff_seconds}s... (Attempt {current_retry+1}/{max_retries+1})")
                except Exception as e:
                    # Catch any other unexpected errors during the request
                    logging.error(f"[TelegramUtils] Unexpected error sending message: {e}. Not retrying.")
                    return False

                if current_retry < max_retries:
                    time.sleep(backoff_seconds)
                    backoff_seconds *= 2 # Exponential backoff
                current_retry += 1
            
            logging.error(f"[TelegramUtils] Failed to send message after {max_retries+1} attempts.")
            return False

    # Note: You might also want to add `import logging` at the top of telegram_utils.py 
    # if you want to use `logging.warning` and `logging.error` as shown above,
    # or replace them with `print()` if you prefer.
    # The main app.py already configures logging.
    ```

This updated method will:
- Attempt to send the message up to `max_retries + 1` times (initial attempt + `max_retries`).
- Start with an `initial_backoff` delay and double it for each subsequent retry (exponential backoff).
- Specifically retry on HTTP status code 429 (Too Many Requests) and 5xx server errors.
- For other HTTP errors (like 400 Bad Request, 401 Unauthorized, 403 Forbidden), it will log the error and fail immediately without retrying, as these usually indicate a problem with the request itself or permissions, not a transient issue.
- Also retry on general `RequestException` errors (like connection timeouts or DNS issues).
- Log warnings for retries and a final error if all attempts fail.

---

## 4. Implement Concurrent Feed Processing

To improve efficiency and prevent one slow feed from blocking others, process the configured Hacker News feeds concurrently using `asyncio.gather`.

**File: `app.py`**

Modify the `run` method in the `HNToTelegramBot` class:

```python
class HNToTelegramBot:
    # ... (other methods: __init__, process_feed) ...

    async def run(self):
        """
        Run the bot: process all configured feeds concurrently.
        """
        # Assuming self.message_delay_seconds is defined in __init__ as per prior suggestion
        # and process_feed expects it as an argument.
        # If process_feed was modified to directly use self.message_delay_seconds,
        # then the call would be self.process_feed(feed)
        
        tasks = [self.process_feed(feed, delay_seconds=self.message_delay_seconds) for feed in self.feeds]
        
        if not tasks:
            logging.info("No feeds configured to process.")
            return

        logging.info(f"Starting concurrent processing for {len(tasks)} feed(s)...")
        
        # asyncio.gather runs all tasks concurrently.
        # If one task raises an exception, gather will propagate that exception.
        # Individual entry processing errors within process_feed should already be caught and logged there.
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            feed_name = self.feeds[i].feed_name # Get feed name for context
            if isinstance(result, Exception):
                logging.error(f"Error processing feed '{feed_name}': {result}")
            else:
                logging.info(f"Successfully finished processing for feed '{feed_name}'.")
        
        logging.info("All feed processing tasks complete.")

# ... (rest of the file, e.g., main function)
```

**Explanation of Changes:**

1.  **Task Creation:**
    - A list of coroutine calls (`self.process_feed(feed, delay_seconds=self.message_delay_seconds)`) is created, one for each feed in `self.feeds`.
    - *Note:* This assumes you've adopted **Option A** from suggestion #2 (Make Message Delay Configurable) where `process_feed` accepts `delay_seconds` as an argument. If you adopted **Option B** (where `process_feed` directly uses `self.message_delay_seconds`), the task creation would be `tasks = [self.process_feed(feed) for feed in self.feeds]`.

2.  **`asyncio.gather(*tasks, return_exceptions=True)`:**
    - `asyncio.gather` is used to run all these tasks concurrently.
    - `*tasks` unpacks the list of tasks into individual arguments for `gather`.
    - `return_exceptions=True` is important here. If a task raises an exception, `gather` will not immediately stop and raise that exception. Instead, it will continue running other tasks, and the exception will be returned as the result for that specific task. This allows you to see if some feeds processed successfully even if others failed.

3.  **Handling Results:**
    - The code then iterates through the `results` from `gather`.
    - It checks if a `result` is an instance of `Exception`. If so, it logs that an error occurred while processing that particular feed.
    - Otherwise, it logs that the feed processing finished (which implies it completed without raising an unhandled exception at the `process_feed` level).

This change will allow the bot to start fetching and processing all feeds around the same time, rather than waiting for each one to complete sequentially. The overall time taken to process all feeds should be closer to the time taken by the longest individual feed processing task.

---

## 5. Outline Unit Test Additions

Adding unit tests will help ensure the reliability of the bot and make future refactoring safer. Below are suggestions for basic unit tests for key components. You'll typically use Python's `unittest` module and its `unittest.mock.patch` functionality.

**General Setup:**
- Create a `tests` directory in your project root.
- Add an empty `__init__.py` to the `tests` directory to make it a package.
- Test files should typically be named `test_*.py` (e.g., `test_hn_rss.py`).

### A. Testing `hn_rss.py` (`HNRSSFeedHandler`)

**File: `tests/test_hn_rss.py`**

```python
import unittest
from unittest.mock import patch, mock_open
import os
import feedparser # Required for mock structure
from hn_rss import HNRSSFeedHandler # Adjust import path if necessary

class TestHNRSSFeedHandler(unittest.TestCase):

    def setUp(self):
        self.feed_name = "testfeed"
        self.feed_url = "http://fakeurl.com/rss"
        self.id_store_dir = "test_ids" # Use a temporary test directory
        self.handler = HNRSSFeedHandler(self.feed_name, self.feed_url, id_store_dir=self.id_store_dir)
        self.last_id_file_path = os.path.join(self.id_store_dir, f"last_hn_{self.feed_name}_id.txt")

        # Create a dummy id_store_dir if it doesn't exist
        if not os.path.exists(self.id_store_dir):
            os.makedirs(self.id_store_dir)

    def tearDown(self):
        # Clean up the dummy id file and directory
        if os.path.exists(self.last_id_file_path):
            os.remove(self.last_id_file_path)
        if os.path.exists(self.id_store_dir):
            # Check if directory is empty before removing
            if not os.listdir(self.id_store_dir):
                 os.rmdir(self.id_store_dir)
            else: # Or remove recursively if other test files might be there
                 pass # import shutil; shutil.rmtree(self.id_store_dir)


    @patch('feedparser.parse')
    def test_fetch_new_entries_no_last_id(self, mock_parse):
        # Mock feedparser.parse to return some sample entries
        mock_feed_data = {
            'entries': [
                {'id': '3', 'title': 'Entry 3'},
                {'id': '2', 'title': 'Entry 2'},
                {'id': '1', 'title': 'Entry 1'},
            ]
        }
        mock_parse.return_value = feedparser.FeedParserDict(mock_feed_data)

        # Mock os.path.exists for get_last_sent_id to simulate no last ID file
        with patch('os.path.exists', return_value=False):
            new_entries = self.handler.fetch_new_entries()

        self.assertEqual(len(new_entries), 3)
        self.assertEqual(new_entries[0]['id'], '1') # Entries should be reversed (newest last)
        self.assertEqual(new_entries[2]['id'], '3')

    @patch('feedparser.parse')
    def test_fetch_new_entries_with_last_id(self, mock_parse):
        mock_feed_data = {
            'entries': [
                {'id': '5', 'title': 'Entry 5'}, # Newest
                {'id': '4', 'title': 'Entry 4'}, # Last sent
                {'id': '3', 'title': 'Entry 3'},
            ]
        }
        mock_parse.return_value = feedparser.FeedParserDict(mock_feed_data)
        last_sent_id = '4'

        # Simulate existing last_id file
        with patch('os.path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data=last_sent_id)) as mock_file:
                new_entries = self.handler.fetch_new_entries()

        self.assertEqual(len(new_entries), 1)
        self.assertEqual(new_entries[0]['id'], '5')

    @patch('feedparser.parse')
    def test_fetch_new_entries_no_new_entries(self, mock_parse):
        mock_feed_data = {
            'entries': [
                {'id': '4', 'title': 'Entry 4'}, # Last sent
                {'id': '3', 'title': 'Entry 3'},
            ]
        }
        mock_parse.return_value = feedparser.FeedParserDict(mock_feed_data)
        last_sent_id = '4'

        with patch('os.path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data=last_sent_id)):
                new_entries = self.handler.fetch_new_entries()

        self.assertEqual(len(new_entries), 0)

    def test_set_and_get_last_sent_id(self):
        test_id = "test_id_123"
        self.handler.set_last_sent_id(test_id)
        retrieved_id = self.handler.get_last_sent_id()
        self.assertEqual(retrieved_id, test_id)
        
        # Ensure file was actually created
        self.assertTrue(os.path.exists(self.last_id_file_path))
        with open(self.last_id_file_path, "r") as f:
            content = f.read().strip()
        self.assertEqual(content, test_id)

if __name__ == '__main__':
    unittest.main()
```

### B. Testing `telegram_utils.py` (`TelegramUtils`)

**File: `tests/test_telegram_utils.py`**

```python
import unittest
from unittest.mock import patch, MagicMock
import os
from telegram_utils import TelegramUtils # Adjust import path
# Assuming the retry logic (max_retries, initial_backoff) from suggestion #3 is implemented

# Mock .env variables for testing
@patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "fake_token", "TELEGRAM_CHANNEL_ID": "fake_channel"})
class TestTelegramUtils(unittest.TestCase):

    def setUp(self):
        self.utils = TelegramUtils() # Will use mocked env vars
        self.message_text = "Hello <b>World</b>"

    @patch('requests.post')
    def test_send_message_success(self, mock_post):
        # Mock a successful response from requests.post
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock() # Does not raise
        mock_post.return_value = mock_response

        result = self.utils.send_message(self.message_text)

        self.assertTrue(result)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['data']['text'], self.message_text)
        self.assertEqual(kwargs['data']['chat_id'], "fake_channel")

    @patch('requests.post')
    @patch('time.sleep') # Mock time.sleep to speed up retry tests
    def test_send_message_retry_then_success(self, mock_sleep, mock_post):
        # Simulate failure (HTTPError 429) then success
        mock_failure_response = MagicMock()
        mock_failure_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=MagicMock(status_code=429))
        
        mock_success_response = MagicMock()
        mock_success_response.raise_for_status = MagicMock()

        mock_post.side_effect = [mock_failure_response, mock_success_response]

        result = self.utils.send_message(self.message_text, max_retries=1, initial_backoff=0.1) # Limit retries for test

        self.assertTrue(result)
        self.assertEqual(mock_post.call_count, 2) # Initial call + 1 retry
        mock_sleep.assert_called_once_with(0.1) # Check backoff sleep

    @patch('requests.post')
    @patch('time.sleep')
    def test_send_message_all_retries_fail_httperror_429(self, mock_sleep, mock_post):
        # Simulate persistent HTTPError 429 failure
        mock_failure_response = MagicMock()
        # Need to mock the response object that HTTPError expects
        mock_http_error_response = MagicMock()
        mock_http_error_response.status_code = 429
        mock_failure_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_http_error_response)
        mock_post.return_value = mock_failure_response

        result = self.utils.send_message(self.message_text, max_retries=2, initial_backoff=0.1)

        self.assertFalse(result)
        self.assertEqual(mock_post.call_count, 3) # Initial + 2 retries
        self.assertEqual(mock_sleep.call_count, 2) # Sleeps before each retry

    @patch('requests.post')
    def test_send_message_fail_non_retryable_httperror(self, mock_post):
        # Simulate HTTPError 400 (Bad Request) - should not retry
        mock_failure_response = MagicMock()
        mock_http_error_response = MagicMock()
        mock_http_error_response.status_code = 400 # Non-retryable error
        mock_failure_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_http_error_response)
        mock_post.return_value = mock_failure_response
        
        result = self.utils.send_message(self.message_text, max_retries=2, initial_backoff=0.1)

        self.assertFalse(result)
        mock_post.assert_called_once() # Should only try once

    @patch('requests.post')
    @patch('time.sleep')
    def test_send_message_fail_request_exception(self, mock_sleep, mock_post):
        # Simulate network error like ConnectionError
        mock_post.side_effect = requests.exceptions.RequestException("Network error")

        result = self.utils.send_message(self.message_text, max_retries=1, initial_backoff=0.1)

        self.assertFalse(result)
        self.assertEqual(mock_post.call_count, 2) # Initial + 1 retry
        mock_sleep.assert_called_once_with(0.1)


if __name__ == '__main__':
    unittest.main()
```

### C. Testing `app.py` (Configurable Delay)

**File: `tests/test_app.py`**

```python
import unittest
from unittest.mock import patch, MagicMock
import os
from app import HNToTelegramBot # Adjust import path
# Assuming suggestion #2 (configurable delay) is implemented

class TestAppConfigurableDelay(unittest.TestCase):

    @patch.dict(os.environ, {"MESSAGE_DELAY_SECONDS": "30.5"})
    @patch('app.TelegramUtils') # Mock dependencies
    @patch('app.MistralSummarizer')
    @patch('app.get_jobs_feed_handler') # Mock feed handlers
    @patch('app.get_frontpage_feed_handler')
    @patch('app.get_bestcomments_feed_handler')
    def test_delay_from_env_variable(self, mock_bc_fh, mock_fp_fh, mock_j_fh, mock_summarizer, mock_tg_utils):
        # Ensure feed handlers are mocked to avoid side effects if they are called in __init__
        mock_j_fh.return_value = MagicMock()
        mock_fp_fh.return_value = MagicMock()
        mock_bc_fh.return_value = MagicMock() # If best_comments is active by default

        bot = HNToTelegramBot(telegram_utils=mock_tg_utils(), summarizer=mock_summarizer())
        self.assertEqual(bot.message_delay_seconds, 30.5)

    @patch.dict(os.environ, {}) # Ensure MESSAGE_DELAY_SECONDS is not set
    @patch.dict(os.environ, {"MESSAGE_DELAY_SECONDS": "invalid_value"}) # Test invalid value
    @patch('app.TelegramUtils')
    @patch('app.MistralSummarizer')
    @patch('app.get_jobs_feed_handler')
    @patch('app.get_frontpage_feed_handler')
    @patch('app.get_bestcomments_feed_handler')
    def test_delay_default_on_invalid_env(self, mock_bc_fh, mock_fp_fh, mock_j_fh, mock_summarizer, mock_tg_utils):
        mock_j_fh.return_value = MagicMock()
        mock_fp_fh.return_value = MagicMock()
        mock_bc_fh.return_value = MagicMock()
        
        bot = HNToTelegramBot(telegram_utils=mock_tg_utils(), summarizer=mock_summarizer())
        # Assuming default is 1200.0 as per suggestion #2
        self.assertEqual(bot.message_delay_seconds, 1200.0) 

    @patch.dict(os.environ, {}) # Ensure MESSAGE_DELAY_SECONDS is not set for default test
    @patch('app.TelegramUtils')
    @patch('app.MistralSummarizer')
    @patch('app.get_jobs_feed_handler')
    @patch('app.get_frontpage_feed_handler')
    @patch('app.get_bestcomments_feed_handler')
    def test_delay_default_when_env_not_set(self, mock_bc_fh, mock_fp_fh, mock_j_fh, mock_summarizer, mock_tg_utils):
        mock_j_fh.return_value = MagicMock()
        mock_fp_fh.return_value = MagicMock()
        mock_bc_fh.return_value = MagicMock()

        bot = HNToTelegramBot(telegram_utils=mock_tg_utils(), summarizer=mock_summarizer())
        # Assuming default is 1200.0
        self.assertEqual(bot.message_delay_seconds, 1200.0)


# To run these tests:
# python -m unittest discover tests
# or
# python tests/test_hn_rss.py (and other files individually)

if __name__ == '__main__':
    unittest.main()
```

These outlines provide a starting point. You might need to adjust imports based on your exact project structure and add more test cases for edge cases or specific behaviors. Remember to install `feedparser` if you run `test_hn_rss.py` directly, as it's imported for creating mock objects.

---

## 6. Outline README.md Updates

The `README.md` file should be updated to reflect the new features and configurations.

**Suggested `README.md` additions/modifications:**

```markdown
# HN to Telegram Bot

Fetches the latest Hacker News posts from various feeds, summarizes them using Mistral AI, and sends the results to a configured Telegram channel.

## Features

-   Fetches posts from Hacker News feeds:
    -   Jobs
    -   Front Page
    -   Best Comments (*New!*)
-   Summarizes post content using Mistral AI.
-   Sends formatted messages to a Telegram channel.
-   Tracks sent posts to avoid duplicates.
-   Configurable delay between messages from the same feed.
-   Concurrent processing of multiple feeds for efficiency. (*New!*)
-   Improved error handling with retries for message sending. (*New!*)

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <your_repo_url>
    cd hn-telegram-bot
    ```

2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate # On Windows: venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure environment variables:**
    Create a `.env` file in the root directory by copying `.env.example` (if you create one) or by creating it manually. Add the following variables:

    ```dotenv
    TELEGRAM_BOT_TOKEN="your_telegram_bot_token"
    TELEGRAM_CHANNEL_ID="your_telegram_channel_id_or_@username"
    
    # Optional: OpenAI API Key if you are using OpenAI for summarization directly
    # OPENAI_API_KEY="your_openai_api_key" 

    # Optional: Delay between messages within the same feed processing cycle
    MESSAGE_DELAY_SECONDS="600" # Default is 1200 (20 minutes), example: 600 for 10 minutes
    ```
    *(Ensure `analyze_raw_data.py` is adapted if `OPENAI_API_KEY` is intended for Mistral or other models)*

## Running the Bot

```bash
python app.py
```

The bot will then periodically fetch new entries from the configured feeds, summarize them, and send them to your Telegram channel. The GitHub Actions workflow in `.github/workflows/hn-telegram-bot.yml` can be used to run this on a schedule.

## Key Components

-   `app.py`: Main application, orchestrates fetching, summarization, and sending.
-   `hn_rss.py`: Handles fetching and parsing Hacker News RSS feeds. Supports Jobs, Front Page, and Best Comments.
-   `telegram_utils.py`: Utilities for sending messages to Telegram, including retry logic.
-   `analyze_raw_data.py`: Contains the summarization logic (e.g., `MistralSummarizer`).
-   `requirements.txt`: Python dependencies.
-   `last_hn_*.txt`: Files used to track the last sent post ID for each feed type.
-   `SUGGESTIONS.md`: This file, containing suggestions for improvements and new features. (*Consider removing this line from the final README if these suggestions are implemented*)

## Development

### Unit Tests

Unit tests are located in the `tests/` directory. To run them:

```bash
python -m unittest discover tests
```
*(Add this section if unit tests from suggestion #5 are implemented)*

---
```

**Key changes to highlight in the README:**

-   **Features Section:**
    -   Add "Best Comments" to the list of feeds.
    -   Mention concurrent processing and improved error handling as new features.
-   **Environment Variables Section:**
    -   Add `MESSAGE_DELAY_SECONDS` and explain its purpose and default value.
-   **Key Components Section:**
    -   Update the description of `hn_rss.py` to include Best Comments.
    -   Update the description of `telegram_utils.py` to mention retry logic.
-   **Development Section (New):**
    -   Add a subsection about running unit tests if they are implemented.

Make sure to adjust any paths or specific details based on the actual implementation.
