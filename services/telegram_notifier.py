import os
import requests
import logging
from typing import List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class TelegramNotifier:
    """
    Service for sending generated threads to a Telegram bot.
    """
    def __init__(self):
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.api_url = f"https://api.telegram.org/{self.bot_token}/sendMessage"

    def send_thread(self, thread: Dict[str, Any]) -> bool:
        """
        Sends a single thread to Telegram with click-to-copy formatting for each tweet.
        """
        if not self.bot_token or not self.chat_id:
            logger.error("Telegram credentials missing. Skipping.")
            return False

        title = thread.get("post_title", "Untitled Thread")
        tweets = thread.get("tweets", [])
        
        if not tweets:
            return False

        # Build the message with individual code blocks for each tweet
        # Using Markdown (not V2) for simplicity as per existing code, 
        # but wrapping each tweet in backticks.
        header = f"📖 *THREAD FOR: {title}*\n{'-'*20}\n"
        
        message_chunks = []
        for i, tweet in enumerate(tweets):
            # Put a newline after the opening backticks to prevent Telegram 
            # from treating the first word as a syntax highlighting language.
            message_chunks.append(f"Tweet {i+1}:\n```\n{tweet}\n```")

        full_message = header + "\n\n".join(message_chunks)

        # Telegram has a 4096 character limit
        if len(full_message) > 4000:
            full_message = full_message[:3997] + "..."

        payload = {
            "chat_id": self.chat_id,
            "text": full_message,
            "parse_mode": "Markdown"
        }
        response = requests.post(self.api_url, json=payload)
        response.raise_for_status()
        logger.info(f"[TELEGRAM] Sent thread: {title}")
        return True

    def send_rejection_notice(self, title: str, reason: str) -> bool:
        """
        Sends a notification about an aborted/rejected thread.
        """
        if not self.bot_token or not self.chat_id:
            return False

        message = f"🚫 *ABORTED THREAD*\n\n*Topic*: {title}\n*Reason*: {reason}"
        
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }
        try:
            response = requests.post(self.api_url, json=payload)
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"[TELEGRAM] Failed to send rejection notice: {e}")
            return False

    def notify_all(self, thread_output: Dict[str, Any]):
        """
        Iterates through selected threads and sends them one by one.
        """
        threads = thread_output.get("selected_threads", [])
        if not threads:
            logger.info("No threads to send to Telegram.")
            return

        logger.info(f"Sending {len(threads)} threads to Telegram...")
        for thread in threads:
            self.send_thread(thread)
