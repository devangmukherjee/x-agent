import requests
import feedparser
import html
import re
import time
import hashlib
import logging
from typing import List
from models import Post

logger = logging.getLogger(__name__)

class RedditProvider:
    """
    Service responsible for fetching and parsing Reddit RSS feeds.
    """
    def __init__(self, user_agent: str = None):
        self.headers = {
            'User-Agent': user_agent or 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self._url_map = {
            'hot': "https://www.reddit.com/r/{}/.rss",
            'new': "https://www.reddit.com/r/{}/new/.rss",
            'top': "https://www.reddit.com/r/{}/top/.rss?t=day",
            'rising': "https://www.reddit.com/r/{}/rising/.rss"
        }

    def fetch_subreddit_posts(self, subreddit: str, filter_type: str = 'hot', limit: int = 5, verbose: bool = False) -> List[Post]:
        url = self._url_map.get(filter_type, self._url_map['hot']).format(subreddit)
        
        posts = []
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code != 200:
                logger.error(f"Error: {subreddit} returned {response.status_code}")
                return []

            feed = feedparser.parse(response.content)
            count = 0
            for entry in feed.entries:
                if count >= limit: break
                
                author = entry.get('author', 'unknown')
                if "automoderator" in author.lower() or "moderator" in author.lower():
                    continue

                # Parse and Clean
                summary_html = entry.get('summary', '')
                clean_text = re.sub('<[^<]+?>', '', summary_html)
                rss_content = html.unescape(clean_text).strip()
                
                link = entry.get('link', '')
                post_id = hashlib.md5(link.encode()).hexdigest()[:10]

                posts.append(Post(
                    id=post_id,
                    title=entry.get('title', 'No Title'),
                    link=link,
                    author=author,
                    subreddit=subreddit,
                    updated=entry.get('updated', 'unknown'),
                    rss_summary=rss_content
                ))
                
                count += 1
                
        except Exception as e:
            logger.error(f"Failed to fetch r/{subreddit}: {e}")
            
        return posts

    def fetch_all(self, subreddits: List[str], posts_per_sub: int = 5, delay: float = 2.0) -> List[Post]:
        all_posts = []
        for i, sub in enumerate(subreddits):
            if i > 0 and delay > 0:
                time.sleep(delay)
            all_posts.extend(self.fetch_subreddit_posts(sub, limit=posts_per_sub))
        return all_posts
