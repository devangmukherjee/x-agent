import requests
import logging
from bs4 import BeautifulSoup
from typing import Optional
from models import Post

logger = logging.getLogger(__name__)

class ContentExtractor:
    """
    Service responsible for deep content fetching from URLs.
    """
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def extract(self, post: Post) -> str:
        url = post.link
        if not url:
            return ""

        # Specialized Reddit JSON handling
        if "reddit.com" in url:
            json_url = url.rstrip('/') + ".json"
            try:
                resp = requests.get(json_url, headers=self.headers, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    return data[0]['data']['children'][0]['data'].get('selftext', '[No selftext]')
            except:
                pass

        # Fallback to BeautifulSoup for external or if JSON fails
        try:
            resp = requests.get(url, headers=self.headers, timeout=10)
            if resp.status_code != 200:
                return f"[Error {resp.status_code}]"

            soup = BeautifulSoup(resp.content, 'html.parser')
            
            # Remove noise
            for s in soup(['script', 'style', 'nav', 'footer', 'header']):
                s.decompose()
            
            text = soup.get_text(separator=' ', strip=True)
            return (text[:5000] + "...") if len(text) > 5000 else text
            
        except Exception as e:
            return f"[Extraction Failed: {e}]"

    def enrich(self, post: Post) -> Post:
        logger.info(f"    Deep fetching: {post.title[:50]}...")
        post.full_content = self.extract(post)
        return post
