import os
import json
import logging
from typing import Dict, Any
from openai import OpenAI
from dotenv import load_dotenv
from models import EditorialDecision

load_dotenv()

logger = logging.getLogger(__name__)

class EditorialJudge:
    """
    Judge-in-the-loop service that evaluates thread quality.
    """
    
    SYSTEM_PROMPT = """You are an editorial judge for Twitter threads aimed at 20-35 year old tech professionals.

Your job: Would YOU stop scrolling for this thread? Would you enjoy reading it?

Audience:
- Software engineers, founders, tech enthusiasts (20-35 years old)
- Interested in tech, startups, stocks, entrepreneurship
- Want FUN, JUICY, ENGAGING content that's entertaining to read

Evaluate the thread below.

Answer STRICTLY in JSON with:
- action: accept | revise | abort
- confidence: number between 0 and 1
- weakness: the single biggest problem (concise)
- suggested_revision: what should change (specific and actionable)

Rules:
- ACCEPT if: Hook is JUICY/clickbait-y + fun to read + easy to follow
- REVISE if: Hook is boring/bland OR thread is confusing
- ABORT only if: Completely uninteresting OR totally off-topic OR unreadable

EMBRACE clickbait-style hooks! "I just realized why X is screwed", "This changes everything", "Everyone's wrong about X" — these are GOOD.
Don't penalize for being provocative or dramatic as long as it's engaging and truthful.
"""

    def __init__(self, model: str = "gpt-5-mini"):
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.model = model

    def evaluate(self, thread_text: str) -> tuple[EditorialDecision, dict]:
        """
        Evaluates a thread and returns an EditorialDecision + usage data.
        """
        logger.info(f"\n[JUDGE] Evaluating thread quality with {self.model}...")
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": f"Thread:\n{thread_text}"}
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
            
            raw_result = json.loads(response.choices[0].message.content)
            
            decision = EditorialDecision(
                action=raw_result.get("action", "abort"),
                confidence=float(raw_result.get("confidence", 0.0)),
                weakness=raw_result.get("weakness", "No weakness provided"),
                suggested_revision=raw_result.get("suggested_revision", "")
            )
            
            logger.info(f"  > Decision  : {decision.action.upper()}")
            logger.info(f"  > Confidence: {decision.confidence}")
            if decision.action != "accept":
                logger.info(f"  > Weakness  : {decision.weakness}")
                if decision.suggested_revision:
                    logger.info(f"  > Suggestion: {decision.suggested_revision}")

            return decision, usage_data
            
        except Exception as e:
            logger.error(f"Editorial Judgment failed: {e}")
            return EditorialDecision(action="abort", confidence=0.0, weakness=str(e), suggested_revision=""), {}
