from dataclasses import dataclass, field
from typing import Optional, Literal

@dataclass
class Post:
    """
    Represents a Reddit post with metadata and content states.
    """
    id: str
    title: str
    link: str
    author: str
    subreddit: str
    updated: str
    rss_summary: str
    full_content: Optional[str] = None
    
    def to_minimal_dict(self) -> dict:
        """
        Returns minimal post data for AI filtering.
        """
        return {
            'id': self.id,
            'title': self.title,
            'rss_summary': self.rss_summary,
            'subreddit': self.subreddit
        }

    def __str__(self) -> str:
        return f"[{self.subreddit}] {self.title} (ID: {self.id})"

@dataclass
class EditorialDecision:
    """
    Structured judgment from the EditorialJudge.
    """
    action: Literal["accept", "revise", "abort"]
    confidence: float
    weakness: str
    suggested_revision: str
