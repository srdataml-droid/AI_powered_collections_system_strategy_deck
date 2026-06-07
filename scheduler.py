"""
scheduler.py — Geldium AI Collections System: The Scheduler
============================================================
This is the alarm clock. It runs forever in the background
and calls agent.run() on a fixed schedule.

Think of it like a cron job — but written in pure Python
so it works on any machine or cloud platform without
needing to configure system-level cron.

HOW TO RUN:
  python scheduler.py

  Leave it running. It will:
    - Run the agent immediately on startup (so you can test it)
    - Then run again every 24 hours at the same time
    - Log every run with a timestamp
    - Keep running even if one run fails

SCHEDULE OPTIONS (easy to change):
  schedule.every(24).hours.do(job)     → every 24 hours
  schedule.every().day.at("09:00").do(job) → every day at 9am
  schedule.every(1).minutes.do(job)    → every minute (for testing)

INSTALL THE SCHEDULE LIBRARY:
  pip install schedule
"""

# ── IMPORTS ──────────────────────────────────────────────────────────────────

from dotenv import load_dotenv
load_dotenv()  # load .env before anything else reads os.getenv()

# schedule  → lightweight Python job scheduler
#             lets you write "run this every 24 hours" in plain English
import schedule

# time      → for the sleep loop that keeps the scheduler alive
import time

# logging   → structured logs
import logging

# datetime  → for timestamps
from datetime import datetime

# agent     → our agent module. We import run() from it.
#             This is why agent.py must be in the same folder.
import agent

# ── LOGGING ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)


# ── THE JOB ───────────────────────────────────────────────────────────────────

def job():
    """
    The function that runs on schedule.
    Wraps agent.run() with error handling so a single failed run
    doesn't kill the entire scheduler.

    Why wrap it?
      If agent.run() raises an unhandled exception, without this wrapper
      the scheduler would crash and stop running entirely.
      With this wrapper, it logs the error and waits for the next scheduled run.
    """
    logger.info(f"⏰ Scheduler triggered agent run at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        summary = agent.run()
        logger.info(
            f"✅ Scheduled run complete — "
            f"High: {summary['high']} | "
            f"Medium: {summary['medium']} | "
            f"Low: {summary['low']}"
        )
    except Exception as e:
        # Log but don't crash — next scheduled run will still happen
        logger.error(f"Scheduled run failed: {e}")
        logger.info("Scheduler will retry at the next scheduled time.")


# ── SETUP SCHEDULE ────────────────────────────────────────────────────────────

# Run every 24 hours
# Change to schedule.every(1).minutes.do(job) for quick testing
schedule.every(24).hours.do(job)

# To run at a specific time every day instead:
# schedule.every().day.at("09:00").do(job)


# ── STARTUP ───────────────────────────────────────────────────────────────────

logger.info("=" * 60)
logger.info("🤖 Geldium AI Agent Scheduler — Starting up")
logger.info("   Schedule: every 24 hours")
logger.info("   Running first job immediately for verification...")
logger.info("=" * 60)

# Run once immediately on startup so you can verify everything works
# without waiting 24 hours for the first scheduled run
job()

logger.info("✅ First run complete. Scheduler is now running.")
logger.info("   Next run in 24 hours. Leave this process running.")
logger.info("   Press Ctrl+C to stop.")


# ── THE INFINITE LOOP ─────────────────────────────────────────────────────────
# This keeps the scheduler alive forever.
#
# How it works:
#   schedule.run_pending() → checks if any jobs are due to run right now
#   time.sleep(60)         → wait 60 seconds before checking again
#
# Why sleep 60 seconds?
#   Checking every second would waste CPU for no reason.
#   60 seconds is frequent enough that scheduled jobs run close to on time.
#   For a 24-hour schedule, being 60 seconds late is perfectly fine.

try:
    while True:
        schedule.run_pending()   # run any jobs that are due
        time.sleep(60)           # wait 60 seconds, then check again

except KeyboardInterrupt:
    # Ctrl+C was pressed — shut down gracefully
    logger.info("\n🛑 Scheduler stopped by user. Goodbye.")