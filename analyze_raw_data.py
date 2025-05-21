"""
Mistral Summarization
--------------------
Provides an async function to summarize a prompt using the Mistral API.

Functions:
- analyze_and_extract: Summarizes a prompt using Mistral and returns the result.
"""

import os
import aiohttp
from typing import Optional
from dotenv import load_dotenv

load_dotenv()
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

class MistralSummarizer:
    """
    Async summarizer using the Mistral API.
    """
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("MISTRAL_API_KEY")
        if not self.api_key:
            raise ValueError("MISTRAL_API_KEY must be set in .env or passed explicitly.")
        self.api_url = "https://api.mistral.ai/v1/chat/completions"

    async def summarize(self, text: str, prompt: Optional[str] = None, max_tokens: int = 512) -> Optional[str]:
        """
        Summarizes the given text using the Mistral API.
        Args:
            text: The text to summarize.
            prompt: Custom prompt for the LLM (should instruct Telegram HTML output).
            max_tokens: Max tokens for the summary.
        Returns:
            The summary string, or None on error.
        """
        prompt = prompt or (
            "Summarize the following Hacker News post for a Telegram channel. "
            "Use Telegram HTML formatting, include emojis, and avoid Markdown."
        )
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "mistral-tiny",
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": text}
            ],
            "max_tokens": max_tokens
        }
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(self.api_url, json=payload, headers=headers, timeout=30) as resp:
                    resp.raise_for_status()
                    data = await resp.json()
                    return data["choices"][0]["message"]["content"]
            except Exception as e:
                print(f"[MistralSummarizer] Error: {e}")
                return None

# For backward compatibility with procedural code
import asyncio
_default_summarizer = MistralSummarizer()
async def summarize_with_mistral(text: str, prompt: Optional[str] = None, max_tokens: int = 512) -> Optional[str]:
    return await _default_summarizer.summarize(text, prompt, max_tokens)