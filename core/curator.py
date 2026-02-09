import logging
from typing import List
from services.reddit_provider import RedditProvider
from services.ai_filter import AIFilter
from services.content_extractor import ContentExtractor
from services.thread_generator import ThreadGenerator
from services.telegram_notifier import TelegramNotifier
from services.editorial_judge import EditorialJudge

logger = logging.getLogger(__name__)

class ContentCurator:
    """
    The main orchestrator for the Reddit-to-Twitter pipeline.
    """
    def __init__(self, filter_model: str = "gpt-5-mini", thread_model: str = "gpt-5.2"):
        self.reddit = RedditProvider()
        self.ai_filter = AIFilter(model=filter_model)
        self.extractor = ContentExtractor()
        self.thread_gen = ThreadGenerator(model=thread_model)
        self.notifier = TelegramNotifier()
        self.judge = EditorialJudge(model="gpt-5.2")

    def run_pipeline(self, subreddits: List[str], posts_per_sub: int = 5) -> dict:
        """
        Executes the full curation workflow using a progressive sequential loop.
        """
        usage_stats = {
            "gpt-5-mini": {"prompt": 0, "completion": 0, "total": 0, "cost": 0.0},
            "gpt-5.2": {"prompt": 0, "completion": 0, "total": 0, "cost": 0.0},
            "total_cost": 0.0
        }

        # Stage 1: Aggregation
        logger.info("\n" + "="*50)
        logger.info("[ORCHESTRATOR] Stage 1: Aggregation")
        logger.info("="*50)
        all_posts = self.reddit.fetch_all(subreddits, posts_per_sub=posts_per_sub)
        logger.info(f"[ORCHESTRATOR] Aggregated {len(all_posts)} posts.")
        
        if not all_posts:
            raise RuntimeError("[ORCHESTRATOR] Stage 1 Failed: No posts aggregated from subreddits.")

        # Stage 2: AI Ranking (Top 10-15)
        logger.info("\n" + "="*50)
        logger.info("[ORCHESTRATOR] Stage 2: AI Ranking & Scoring")
        logger.info("="*50)
        ranked_data, filter_usage = self.ai_filter.filter(all_posts)
        if filter_usage:
            self._update_usage(usage_stats, filter_usage)

        if not ranked_data:
            logger.warning("[ORCHESTRATOR] Stage 2 Failed: No posts ranked by AI.")
            return {"posts": [], "output": {"selected_threads": []}, "usage": usage_stats}

        # Stage 3-5: Progressive Sequential Loop (Fetch -> Gen -> Judge)
        logger.info("\n" + "="*50)
        logger.info("[ORCHESTRATOR] Stage 3-5: Progressive Editorial Loop")
        logger.info("="*50)
        
        approved_threads = []
        best_thread_so_far = None
        best_judge_score = -1.0
        
        # We loop through top 10 candidates max, but stop at 3 approved
        for i, rank_item in enumerate(ranked_data[:10]):
            post_id = rank_item['id']
            score = rank_item['score']
            post = next((p for p in all_posts if p.id == post_id), None)
            
            if not post: continue
            
            logger.info(f"\n[ORCHESTRATOR] Processing Candidate {i+1} (Score: {score}): {post.title[:60]}...")
            
            # 1. Selective Enrichment (Deep Fetch)
            enriched_post = self.extractor.enrich(post)
            
            # 2. Thread Generation
            # Note: generate_threads expects a list, so we wrap it
            gen_output, gen_usage = self.thread_gen.generate_threads([enriched_post])
            if gen_usage:
                self._update_usage(usage_stats, gen_usage)
            
            if not gen_output.get("selected_threads"):
                continue
            
            current_thread = gen_output["selected_threads"][0]
            
            # 3. Editorial Judgment (Agentic Loop with Revisions)
            final_thread, loop_approved = self._process_single_thread(current_thread, usage_stats)
            
            if loop_approved:
                approved_threads.append(final_thread)
                logger.info(f"[ORCHESTRATOR] ✅ THREAD APPROVED ({len(approved_threads)}/3)")
                if len(approved_threads) >= 3:
                    logger.info("[ORCHESTRATOR] Quota reached (3 threads). Stopping loop.")
                    break
            else:
                # Track the best rejected thread just in case we hit 0 total
                # Use judge confidence or initial score as a heuristic
                if score > best_judge_score:
                    best_judge_score = score
                    best_thread_so_far = final_thread

        # Fallback Logic: Ensure at least one thread is sent if we scanned enough and found nothing "perfect"
        if not approved_threads and best_thread_so_far:
            logger.info("\n" + "!"*50)
            logger.info("[ORCHESTRATOR] FALLBACK TRIGGERED: Sending best candidate so far.")
            logger.info("!"*50)
            approved_threads.append(best_thread_so_far)

        # Stage 6: Telegram Notification
        if approved_threads:
            logger.info(f"\n[ORCHESTRATOR] Stage 6: Telegram Notification ({len(approved_threads)} threads)...")
            self.notifier.notify_all({"selected_threads": approved_threads})
        else:
            logger.info("\n[ORCHESTRATOR] Stage 6: Skipping Telegram (No threads available).")

        logger.info("\n[ORCHESTRATOR] Pipeline complete.")
        return {
            "posts": [], # No longer maintaining a separate curated_posts list
            "output": {"selected_threads": approved_threads},
            "usage": usage_stats
        }

    def _process_single_thread(self, thread: dict, usage_stats: dict) -> tuple[dict, bool]:
        """
        Handles the editorial judgment for a single thread (no revisions).
        Returns (thread, is_approved).
        """
        post_title = thread.get('post_title', 'Untitled')
        
        # Single judgment call
        thread_text = "\n\n".join(thread.get("tweets", []))
        decision, judge_usage = self.judge.evaluate(thread_text)
        if judge_usage:
            self._update_usage(usage_stats, judge_usage)

        if decision.action == "accept":
            return thread, True

        # Reject (either revise or abort - we treat both as rejection to save costs)
        reason = decision.weakness
        logger.warning(f"\n[ORCHESTRATOR] 🚫 REJECTED: {post_title[:50]}...")
        logger.warning(f"  Reason: {reason}")
        
        self.notifier.send_rejection_notice(post_title, reason)
        return thread, False

    def _update_usage(self, usage_stats: dict, usage_data: dict):
        """
        Aggregates token usage and costs.
        """
        model = usage_data.get("model")
        # Map specific models to buckets if needed, but here we use exact model names in usage_stats
        if model not in usage_stats:
            usage_stats[model] = {"prompt": 0, "completion": 0, "total": 0, "cost": 0.0}
            
        usage_stats[model]["prompt"] += usage_data.get("prompt_tokens", 0)
        usage_stats[model]["completion"] += usage_data.get("completion_tokens", 0)
        usage_stats[model]["total"] += usage_data.get("total_tokens", 0)
        
        # Calculate cost if not provided (fallback rates)
        cost = usage_data.get("cost", 0.0)
        if not cost:
            if "gpt-5-mini" in model:
                cost = (usage_data["prompt_tokens"] * 0.15 / 1000000) + (usage_data["completion_tokens"] * 0.6 / 1000000)
            elif "gpt-5.2" in model:
                cost = (usage_data["prompt_tokens"] * 10.0 / 1000000) + (usage_data["completion_tokens"] * 30.0 / 1000000)
        
        usage_stats[model]["cost"] += cost
        usage_stats["total_cost"] += cost
