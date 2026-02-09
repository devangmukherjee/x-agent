# 🤖 x-agent: The AI Reddit-to-Twitter Curator

`x-agent` is an intelligent, automated pipeline that scours Reddit for high-signal tech and startup content, then uses advanced LLMs to craft and vet high-engagement Twitter threads. It's designed to run autonomously on AWS, sending its "winning" threads directly to a Telegram bot for final review or publishing.

---

## 🏗 Architecture & Workflow

The system operates in a multi-stage "Progressive Editorial Loop" to ensure maximum quality while keeping LLM costs low.

1.  **Aggregation**: The agent monitors a list of target subreddits (e.g., `r/technology`, `r/ExperiencedDevs`) via RSS.
2.  **AI Ranking (The "Filter")**: A fast, inexpensive LLM (`gpt-5-mini`) performs a first pass, scoring 50+ posts based on novelty, relevance, and signal density.
3.  **The Editorial Loop**: For the top-ranked candidates, the system enters a deep-processing cycle:
    *   **Deep Fetching**: `ContentExtractor` pulls the full text of the post or article (going beyond the summary).
    *   **Thread Generation**: A high-capability LLM (`gpt-5.2`) writes a 6-8 tweet thread written in the persona of a savvy 25-year-old AWS engineer.
    *   **Editorial Judgment**: A separate "Judge" LLM vets the thread. If the hook isn't "scroll-stopping" or the content is weak, the thread is rejected.
4.  **Notification**: Approved threads are instantly dispatched to your Telegram bot.

---

## ☁️ Hosting on AWS

This agent is designed to run serverless once per day to keep your feed fresh with minimal cost.

### 1. Lambda & EventBridge Setup
1.  **Package**: Zip your project files and dependencies into a `deployment.zip`.
2.  **Create Lambda**: Upload the zip to an AWS Lambda function (Python 3.12+).
3.  **Handler**: Set the handler to `main.handler` (if using the Lambda entry point).
4.  **Environment Variables**: Add your `OPENAI_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, and `SUBREDDITS` in the Lambda configuration.
5.  **Schedule**: Use **Amazon EventBridge** to create a "Scheduled Rule" (e.g., `cron(0 12 * * ? *)`) to trigger your Lambda once every 24 hours.

---

## 🛠 Local Setup

1.  **Clone the repo**:
    ```bash
    git clone https://github.com/devangmukherjee/x-agent.git
    cd x-agent
    ```
2.  **Install dependencies**:
    ```bash
    python -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```
3.  **Configure environment**:
    Copy `.env.example` to `.env` and fill in your keys:
    ```bash
    OPENAI_API_KEY=sk-...
    TELEGRAM_BOT_TOKEN=...
    TELEGRAM_CHAT_ID=...
    SUBREDDITS=technology,startups,wallstreetbets
    ```
4.  **Run**:
    ```bash
    python main.py
    ```

---

## 📊 Performance & Cost Audit
The system includes built-in cost auditing. At the end of every run, it prints a breakdown of token usage and the exact USD cost across different models used.
