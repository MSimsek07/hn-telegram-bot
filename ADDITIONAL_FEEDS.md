# Adding Additional Hacker News RSS Feeds

This document provides guidance on how to extend the HN Telegram Bot to include more types of feeds from Hacker News, beyond the initially configured "Jobs," "Front Page," and the suggested "Best Comments."

The bot uses `hnrss.org` as its source, which provides a wide variety of RSS feeds.

## General Process for Adding a New Feed Type

The bot's architecture, particularly the `HNRSSFeedHandler` class in `hn_rss.py`, is designed to be quite generic. Adding a new type of feed typically follows these steps:

1.  **Identify the Feed URL:**
    Determine the exact URL for the new feed from `hnrss.org`. For example:
    - Ask HN: `https://hnrss.org/ask`
    - Show HN: `https://hnrss.org/show`
    - Newest Posts: `https://hnrss.org/newest`

2.  **Modify `hn_rss.py`:**
    *   **Add a URL Constant:** Define a new constant for the feed's URL at the top of the file.
        ```python
        # Example for Ask HN
        HN_ASK_URL = "https://hnrss.org/ask"
        ```
    *   **Create a Factory Function:** Add a new factory function similar to `get_jobs_feed_handler()` or `get_bestcomments_feed_handler()`. This function will instantiate `HNRSSFeedHandler` with the specific name and URL for the new feed.
        ```python
        # Example for Ask HN
        def get_ask_hn_feed_handler(id_store_dir: Optional[str] = None) -> HNRSSFeedHandler:
            return HNRSSFeedHandler("askhn", HN_ASK_URL, id_store_dir) 
            # Note: "askhn" will be used for the last_id filename, e.g., last_hn_askhn_id.txt
        ```
        It's important to choose a unique `feed_name` (the first argument to `HNRSSFeedHandler`) as this name is used to create the `.txt` file that tracks the last sent post ID (e.g., `last_hn_askhn_id.txt`).

3.  **Modify `app.py`:**
    *   **Import the New Handler:** Add the newly created factory function to the imports from `hn_rss.py`.
        ```python
        # Example for Ask HN
        from hn_rss import get_jobs_feed_handler, get_frontpage_feed_handler, get_bestcomments_feed_handler, get_ask_hn_feed_handler
        ```
    *   **Add to Feed List:** In the `HNToTelegramBot` class's `__init__` method, add an instance of the new feed handler to the `self.feeds` list.
        ```python
        self.feeds = [
            get_jobs_feed_handler(),
            get_frontpage_feed_handler(),
            get_bestcomments_feed_handler(), 
            get_ask_hn_feed_handler(), # Add this line
        ]
        ```

4.  **Run the Bot:**
    Upon the next run, the bot will automatically:
    -   Attempt to find a `last_hn_<feed_name>_id.txt` file for the new feed.
    -   If not found (which will be the case for a brand new feed), it will fetch all current entries from the RSS feed (up to the feed's default limit, usually 20).
    -   Process (summarize, if applicable) and send these entries to Telegram according to the configured delay.
    -   Create/update the `last_hn_<feed_name>_id.txt` file with the ID of the last entry it processed.

This general process allows for easy extension to most static feed types available on `hnrss.org`. More complex feeds, like those requiring search parameters or user IDs, might require slight modifications to `HNRSSFeedHandler` or new handlers if the URL structure or ID tracking becomes significantly different.

---

## Specific Considerations for New Feeds

While the general integration process is straightforward, different types of Hacker News feeds might warrant special considerations:

1.  **Content Structure and `entry.summary`:**
    *   **Standard Story Feeds (Front Page, Newest, Best):** For these feeds, `entry.title` is the story title, and `entry.link` points to the external article. The `entry.summary` (or `entry.description` as feedparser might call it) often contains the text of the article itself, or comments if the link is to an HN discussion. The current summarization prompt (`entry.title + "\n" + getattr(entry, "summary", "")`) is generally well-suited for these.
    *   **"Ask HN" Feeds:** For "Ask HN" posts, the `entry.title` is the question (e.g., "Ask HN: How do you manage your dotfiles?"). The `entry.link` points to the HN discussion page for that question. The `entry.summary` often contains the body of the Ask HN post itself, which might include additional context or clarification from the original poster.
    *   **"Show HN" Feeds:** Similar to "Ask HN," `entry.title` is the project title (e.g., "Show HN: I built a new RSS reader"). `entry.link` points to the HN discussion. `entry.summary` often contains the descriptive text provided by the author about their project.
    *   **"Jobs" Feed:** `entry.title` is the job posting title. `entry.summary` usually contains the job description.
    *   **"Best Comments" Feed:** `entry.title` is typically "Comment by [username] on [Original Post Title]". `entry.link` points directly to the comment. `entry.summary` contains the text of the comment itself.

2.  **Summarization Strategy:**
    *   **Full Summarization:** For feeds like "Front Page," "Newest," "Best," and "Show HN" (where the summary often describes a project), the current summarization approach is likely beneficial to provide a concise overview.
    *   **Partial or No Summarization for Comments:** For "Best Comments," the `entry.summary` *is* the comment. Summarizing a comment might not always be ideal as the nuance could be lost. You might consider:
        *   Sending the comment text directly (if it's within Telegram's message length limits).
        *   Using a different summarization prompt for comments, perhaps focused on extracting the key point if the comment is very long.
        *   Truncating long comments with a "read more" link.
    *   **"Ask HN" Questions:** The `entry.title` is the question. The `entry.summary` (body of the Ask HN) might provide useful context. Summarizing the title and body together could be useful, or you might choose to present the question (title) prominently and the body as additional detail, possibly summarized if long.
    *   **"Jobs":** Job descriptions (`entry.summary`) can be long. Summarization is useful here.

3.  **Telegram Message Formatting:**
    *   The current format is:
        ```
        <b>{entry.title}</b>
        <a href='{entry.link}'>Read more</a>

        {summary}
        ```
    *   For "Best Comments," where the title already indicates it's a comment, and the link goes to the comment, this format is okay.
    *   For "Ask HN," you might want to clearly label it as a question, e.g., "<b>Ask HN:</b> {entry.title}".
    *   For "Show HN," similarly, "<b>Show HN:</b> {entry.title}".
    *   Consider if the "Read more" text is always appropriate. For comments, it might be "View comment" or "Read thread."

4.  **Advanced Filtering and Parameterized Feeds:**
    *   `hnrss.org` allows parameters like `points=N` or `q=KEYWORD` on many feeds.
    *   If you wanted to subscribe to, for example, "Newest posts with >100 points" or "'Ask HN' posts containing 'Python'", this would require a more dynamic `HNRSSFeedHandler`.
    *   The `feed_name` used for the `last_id` file would need to incorporate these parameters to be unique (e.g., `last_hn_newest_points_100_id.txt`).
    *   The factory functions would need to accept these parameters to construct the correct URL and feed name.
    *   This is a more significant architectural change if fine-grained, user-configurable filtering per feed is desired. For now, adding distinct static feeds is simpler.

5.  **User-Specific Feeds (e.g., `submitted?id=USERNAME`):**
    *   These require a `USERNAME` in the URL.
    *   To implement this generally, you'd likely need:
        *   A way to configure a list of usernames to track.
        *   Dynamically create handlers for each user, possibly modifying `HNRSSFeedHandler` to accept the username as a parameter and incorporate it into the `feed_name` (e.g., `last_hn_submitted_pg_id.txt`).

These considerations can help you tailor the bot's behavior for each new feed type, making the information more relevant and well-presented to your Telegram channel audience.

---

## Concrete Examples: Adding "Ask HN" and "Show HN"

Let's illustrate the process by adding support for "Ask HN" and "Show HN" feeds.

### 1. Modify `hn_rss.py`

First, add the URL constants and their respective factory functions.

```python
# hn_rss.py

# ... (other imports and existing URL constants like HN_JOBS_URL) ...

# New URL Constants
HN_ASK_URL = "https://hnrss.org/ask"
HN_SHOW_URL = "https://hnrss.org/show"

# ... (existing HNRSSFeedHandler class) ...

# Existing factory functions (get_jobs_feed_handler, etc.)
# ...

# New Factory Functions
def get_ask_hn_feed_handler(id_store_dir: Optional[str] = None) -> HNRSSFeedHandler:
    """Factory for 'Ask HN' feed handler."""
    return HNRSSFeedHandler(feed_name="askhn", feed_url=HN_ASK_URL, id_store_dir=id_store_dir)

def get_show_hn_feed_handler(id_store_dir: Optional[str] = None) -> HNRSSFeedHandler:
    """Factory for 'Show HN' feed handler."""
    return HNRSSFeedHandler(feed_name="showhn", feed_url=HN_SHOW_URL, id_store_dir=id_store_dir)

```

**Key points for `hn_rss.py`:**
-   `HN_ASK_URL` and `HN_SHOW_URL` are defined.
-   `get_ask_hn_feed_handler` creates a handler for "Ask HN" posts. The `feed_name` is `"askhn"`, so it will use `last_hn_askhn_id.txt`.
-   `get_show_hn_feed_handler` creates a handler for "Show HN" posts. The `feed_name` is `"showhn"`, so it will use `last_hn_showhn_id.txt`.

### 2. Modify `app.py`

Next, import these new handlers and add them to the bot's feed list.

```python
# app.py

# ... (other imports) ...
# Import the new handlers along with existing ones
from hn_rss import (
    get_jobs_feed_handler, 
    get_frontpage_feed_handler, 
    get_bestcomments_feed_handler, # Assuming this is already added
    get_ask_hn_feed_handler,      # New import
    get_show_hn_feed_handler      # New import
)
# ... (MistralSummarizer, TelegramUtils, logging setup) ...

class HNToTelegramBot:
    def __init__(self, telegram_utils: TelegramUtils = None, summarizer: MistralSummarizer = None):
        self.telegram_utils = telegram_utils or TelegramUtils()
        self.summarizer = summarizer or MistralSummarizer()
        
        # Add the new handlers to the list of feeds
        self.feeds = [
            get_jobs_feed_handler(),
            get_frontpage_feed_handler(),
            get_bestcomments_feed_handler(), # Assumed present
            get_ask_hn_feed_handler(),       # Added
            get_show_hn_feed_handler(),      # Added
        ]
        
        # ... (rest of __init__, e.g., loading message_delay_seconds) ...

    # ... (process_feed method) ...

    # ... (run method) ...

# ... (main function) ...
```

**Key points for `app.py`:**
-   The new factory functions (`get_ask_hn_feed_handler`, `get_show_hn_feed_handler`) are imported.
-   Instances of these handlers are added to the `self.feeds` list in `HNToTelegramBot.__init__`.

### Next Steps After Implementation

-   **Testing:** Run the bot. It should now fetch "Ask HN" and "Show HN" posts. Check your Telegram channel.
-   **Summarization/Formatting (Review):** Observe how these new types of posts are summarized and formatted. As discussed in "Specific Considerations," you might want to:
    -   Adjust the summarization prompt for "Ask HN" questions or "Show HN" descriptions if needed.
    -   Modify the Telegram message template in `app.py` if you want to add prefixes like "Ask HN:" or change the "Read more" link text for these specific feeds. This would likely involve passing the `feed_handler.feed_name` to the message formatting part of `process_feed` and having conditional logic there.

By following these examples, you can similarly add other static feeds like "Newest" (`https://hnrss.org/newest`), "Polls" (`https://hnrss.org/polls`), etc. Remember to choose a unique `feed_name` for each to ensure proper tracking of sent items.
