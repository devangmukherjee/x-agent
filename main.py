import os
import logging
from core.curator import ContentCurator

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger()

# Silence verbose third-party logging
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)

def main():
    # 1. Configuration (Required via env)
    subreddits_env = os.getenv("SUBREDDITS")
    if not subreddits_env:
        raise ValueError("Environment variable 'SUBREDDITS' is required (comma-separated list).")
    
    subreddits = [s.strip() for s in subreddits_env.split(",") if s.strip()]

    posts_per_sub = int(os.getenv("POSTS_PER_SUB", "3"))

    filter_model = os.getenv("FILTER_MODEL", "gpt-5-mini")
    thread_model = os.getenv("THREAD_MODEL", "gpt-5.2")

    # 2. Initialize Curator
    curator = ContentCurator(
        filter_model=filter_model,
        thread_model=thread_model
    )

    logger.info("==================================================")
    logger.info("🚀 REDDIT TWEET AGENT: FULL PIPELINE START")
    logger.info("==================================================")

    try:
        pipeline_result = curator.run_pipeline(
            subreddits=subreddits,
            posts_per_sub=posts_per_sub
        )
    except Exception as e:
        logger.error(f"❌ PIPELINE ABORTED: {e}")
        raise e

    usage = pipeline_result["usage"]

    # 3. Usage Audit
    logger.info("==================================================")
    logger.info("📊 PIPELINE USAGE AUDIT")
    logger.info("==================================================")
    
    # Sort keys to keep it consistent
    for model_name, stats in usage.items():
        if model_name == "total_cost":
            continue
        logger.info(
            f"- {model_name:15}: {stats['total']:5} tokens (P:{stats['prompt']:4}, C:{stats['completion']:4}) | ${stats['cost']:.6f}"
        )
    
    logger.info(f"🚀 GRAND TOTAL COST: ${usage['total_cost']:.6f}")

    logger.info("==================================================")
    logger.info("FINISHED")
    logger.info("==================================================")


if __name__ == "__main__":
    # Ensure local runs show output even if logger isn't configured by Lambda
    if not logger.handlers:
        logging.basicConfig(level=logging.INFO, format='%(message)s')
    main()