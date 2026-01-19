"""
Daily Sync Scheduler

Runs automatic syncs at configured intervals.
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import logging
import os

from database import SessionLocal
from sync_service import sync_all_institutions, SimpleFINSyncService

logger = logging.getLogger(__name__)

# Get timezone from environment or default to local system timezone
TIMEZONE = os.getenv("TZ", None)  # e.g., "America/Chicago", "America/New_York"

scheduler = BackgroundScheduler(timezone=TIMEZONE) if TIMEZONE else BackgroundScheduler()


def daily_sync_job():
    """Job that runs daily to sync all institutions"""
    logger.info(f"Starting daily sync at {datetime.now()}")

    db = SessionLocal()
    try:
        results = sync_all_institutions(db)

        # Log results
        for result in results:
            if "error" in result:
                logger.error(f"Sync failed for {result.get('institution', 'unknown')}: {result['error']}")
            else:
                logger.info(
                    f"Synced {result['institution']}: "
                    f"{result['accounts_synced']} accounts, "
                    f"{result['transactions_added']} new transactions"
                )

        # Calculate net worth
        sync_service = SimpleFINSyncService(db)
        nw = sync_service.calculate_net_worth()
        logger.info(f"Net worth updated: ${nw.net_worth:,.2f}")

    except Exception as e:
        logger.error(f"Daily sync failed: {e}")
    finally:
        db.close()

    logger.info("Daily sync completed")


def start_scheduler():
    """Start the background scheduler"""
    # Run sync daily at 6 AM
    scheduler.add_job(
        daily_sync_job,
        CronTrigger(hour=6, minute=0),
        id="daily_sync",
        name="Daily Financial Sync",
        replace_existing=True
    )

    # Also run every 4 hours for more frequent updates
    scheduler.add_job(
        daily_sync_job,
        CronTrigger(hour="*/4"),
        id="periodic_sync",
        name="Periodic Financial Sync",
        replace_existing=True
    )

    scheduler.start()
    logger.info("Scheduler started - syncing daily at 6 AM and every 4 hours")


def stop_scheduler():
    """Stop the scheduler"""
    scheduler.shutdown()
    logger.info("Scheduler stopped")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Running manual sync...")
    daily_sync_job()
