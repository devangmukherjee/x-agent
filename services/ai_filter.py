import os
import json
import logging
from typing import List
from openai import OpenAI
from dotenv import load_dotenv
from models import Post

load_dotenv()

logger = logging.getLogger(__name__)

class AIFilter:
    """
    Service for Stage 1 post curation using OpenAI.
    """
    SYSTEM_PROMPT = """You are a tech content curator for Twitter. Your goal is to identify the TOP 10-15 Reddit posts that would make engaging, informative tweets for a smart 20–30 y/o Software Engineer audience.

UNIVERSAL INTERESTINGNESS RUBRIC:
Evaluate every post against these base criteria:
1. **Novelty**: Is this new, surprising, or counterintuitive?
2. **Relevance**: Would a smart 20–30 y/o SWE care? (Tech, startups, entrepreneurship, finance/stocks).
3. **Signal Density**: Is there a genuine insight or valuable info, not just news or noise?

SCORING:
Assign each post a score from 0-100 based on the rubric.

OUTPUT FORMAT:
Return a JSON object containing a list of ranked posts with their scores, sorted by score descending.
Example: 
{
  "ranked_posts": [
    {"id": "id1", "score": 92},
    {"id": "id2", "score": 85},
    {"id": "id3", "score": 78},
    ...
  ]
}
"""

    def __init__(self, model: str = "gpt-5-mini"):
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.model = model

    def filter(self, posts: List[Post], title_limit: int = 300, summary_limit: int = 1500) -> List[str]:
        if not posts:
            return []

        # Prepare payload with truncation
        payload = []
        for p in posts:
            title = (p.title[:title_limit-3] + "...") if len(p.title) > title_limit else p.title
            summary = (p.rss_summary[:summary_limit-3] + "...") if len(p.rss_summary) > summary_limit else p.rss_summary
            payload.append({
                'id': p.id,
                'title': title,
                'rss_summary': summary,
                'subreddit': p.subreddit
            })

        try:
            formatted_data = json.dumps(payload, indent=2)
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": f"Curate these posts:\n\n{formatted_data}"}
                ],
                response_format={ "type": "json_object" }
            )
            
            # Log usage and cost
            usage = response.usage
            prompt_tokens = usage.prompt_tokens
            completion_tokens = usage.completion_tokens
            total_tokens = usage.total_tokens
            
            # gpt-5-mini approx rates
            cost = (prompt_tokens * 0.15 / 1000000) + (completion_tokens * 0.60 / 1000000)
            
            usage_data = {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "cost": cost,
                "model": self.model
            }
            
            result = json.loads(response.choices[0].message.content)
            ranked_posts = result.get('ranked_posts', [])
            return ranked_posts[:15], usage_data
            
        except Exception as e:
            logger.error(f"AI Filtering failed: {e}")
            return [], {}
