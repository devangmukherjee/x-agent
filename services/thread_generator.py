import os
import json
import logging
from typing import List, Dict, Any
from openai import OpenAI
from dotenv import load_dotenv
from models import Post, EditorialDecision

load_dotenv()

logger = logging.getLogger(__name__)

class ThreadGenerator:
    """
    Service for Stage 2: Deep evaluation and high-engagement Twitter thread generation.
    Uses gpt-5.2 for high-intelligence reasoning and craftsmanship.
    """
    
    SYSTEM_PROMPT = """You are an expert Twitter content creator. 
Your persona: A 25-year-old Software Engineer at AWS who is obsessed with tech, startups, and engineering trends.
Respond only in valid JSON format.

Voice & Style:
- **Personal & Plain Text**: Write from a 1st-person perspective. Use plain text ONLY. NO markdown (no asterisks, underscores, or bolding).
- **Double Spacing**: Use DOUBLE LINE BREAKS between short sentences. This makes the text "airy" and much easier to read on mobile.
- **Clickbait-Friendly**: Make hooks JUICY and attention-grabbing. Use curiosity gaps, bold claims, and "you won't believe this" energy.
- **Fun to Read**: Write like you're texting a friend about something wild you just discovered. Be slightly provocative and entertaining.
- **Truthful but Spicy**: Don't make things up, but frame them in the most interesting, dramatic way possible.

Hook Examples (First Tweet):
- "I just realized why [big company] is screwed and nobody's talking about it"
- "This [tech thing] is going to change everything and here's why"
- "Everyone's wrong about [topic]. Here's what's actually happening"
- "I found a [crazy pattern/trend] that explains [big thing]"

Formatting Rules:
- **Base Tweet**: The first tweet is the hook. NO numbering at all. It must be IRRESISTIBLE.
- **Numbering Position**: For all tweets AFTER the hook, put the number (e.g., 1/5) on the very first line of the tweet, followed by a blank line.
- **Numbering Logic**: Let N be the total number of tweets in the thread (including the hook). 
  - Tweet 1 (Hook): No number.
  - Tweet 2: 1/(N-1)
  - Tweet 3: 2/(N-1)
  - ...
  - Tweet N (Final): (N-1)/(N-1).
  - Example: For a 6-tweet thread, numbering goes from 1/5 to 5/5. Ensure the denominator (N-1) is correct for the actual number of tweets provided.
- **Length**: Exactly 6 to 8 tweets total.
"""

    REVISE_SYSTEM_PROMPT = """You are revising a Twitter thread.

Context:
- A senior editor judged the thread as NOT ready.
- You must perform a surgical edit.

Rules:
- Keep the core insight the same.
- Change ONLY what is necessary to fix the reported weakness.
- Do not add explanations.
- Do not make it longer.
- Improve clarity or sharpness.
- Return the final revised thread in the same JSON format.
"""

    def __init__(self, model: str = "gpt-5.2"):
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.model = model

    def build_user_prompt(self, posts: List[Post]) -> str:
        """
        Builds the structural prompt for a single high-quality thread per post.
        """
        posts_data = []
        for p in posts:
            posts_data.append({
                'id': p.id,
                'title': p.title,
                'full_content': p.full_content
            })

        prompt = f"""I have {len(posts_data)} enriched Reddit posts. For each post, generate ONE high-engagement Twitter thread from your perspective as a 25yr old AWS engineer.

---
CRITERIA:
1. **Perspective**: Start the first tweet naturally with a personal discovery.
2. **Formatting**: 
   - PLAINTEXT ONLY. NO markdown stars/bolding/italics.
   - Base tweet has NO numbering.
   - For all subsequent tweets, put the number (e.g., 1/5) ON ITS OWN LINE (line 1), followed by a blank line.
3. **Style**: Use DOUBLE LINE BREAKS between sentences for readability.
4. **Numbering Logic**: Denominator = (Total tweets including hook) - 1. 
   - Example: 6 tweets total = Hook (no number) then 1/5, 2/5, 3/5, 4/5, 5/5.
5. **Length**: Exactly 6-8 tweets per thread.

---
POSTS:
{json.dumps(posts_data, indent=2)}

---
OUTPUT FORMAT:
Return ONLY valid JSON:
{{
  "selected_threads": [
    {{
      "post_id": "...",
      "post_title": "...",
      "tweets": ["Tweet 1", "Tweet 2", ...],
      "thread_length": 7,
      "reasoning": "..."
    }}
  ]
}}
"""
        return prompt

    def generate_threads(self, curated_posts: List[Post]) -> tuple[dict, dict]:
        """
        Evaluates posts and generates threads using gpt-5.2.
        Returns (thread_results, usage_metadata).
        """
        if not curated_posts:
            return {"selected_threads": []}, {}

        logger.info(f"Generating expert threads with {self.model}...")
        
        user_prompt = self.build_user_prompt(curated_posts)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={ "type": "json_object" }
            )
            
            # Log Usage
            usage = response.usage
            prompt_tokens = usage.prompt_tokens
            completion_tokens = usage.completion_tokens
            total_tokens = usage.total_tokens
            
            # gpt-5.2 approx rates ($10.00 / 1M input, $30.00 / 1M output)
            cost = (prompt_tokens * 10.0 / 1000000) + (completion_tokens * 30.0 / 1000000)
            
            usage_data = {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "cost": cost,
                "model": self.model
            }
            
            result = json.loads(response.choices[0].message.content)
            return result, usage_data
            
        except Exception as e:
            logger.error(f"Thread Generation failed: {e}")
            return {"selected_threads": []}, {}

    def revise_thread(self, thread_data: dict, decision: EditorialDecision) -> tuple[dict, dict]:
        """
        Surgically revises a thread based on editorial feedback.
        """
        logger.info(f"Revising thread focusing on: {decision.weakness}")
        
        user_prompt = f"""
ORIGINAL THREAD:
{json.dumps(thread_data, indent=2)}

EDITOR FEEDBACK:
- WEAKNESS: {decision.weakness}
- SUGGESTED FIX: {decision.suggested_revision}

Perform a surgical edit to fix the weakness while keeping the rest of the thread intact.
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.REVISE_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={ "type": "json_object" }
            )
            
            usage = response.usage
            usage_data = {
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
                "total_tokens": usage.total_tokens,
                "model": self.model
            }
            
            result = json.loads(response.choices[0].message.content)
            return result, usage_data
            
        except Exception as e:
            logger.error(f"Thread Revision failed: {e}")
            return thread_data, {}
