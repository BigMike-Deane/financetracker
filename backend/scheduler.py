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
from sync_service import sync_all_institutions, quick_sync_all_institutions, SimpleFINSyncService

logger = logging.getLogger(__name__)

# Get timezone from environment or default to local system timezone
TIMEZONE = os.getenv("TZ", None)  # e.g., "America/Chicago", "America/New_York"

scheduler = BackgroundScheduler(timezone=TIMEZONE) if TIMEZONE else BackgroundScheduler()


def quick_sync_job():
    """Job that runs hourly to update balances only (fast)"""
    logger.info(f"Starting quick sync at {datetime.now()}")

    db = SessionLocal()
    try:
        results = quick_sync_all_institutions(db)

        # Log results
        total_accounts = sum(r.get('accounts_synced', 0) for r in results if 'accounts_synced' in r)
        errors = [r for r in results if 'error' in r]

        if errors:
            for err in errors:
                logger.error(f"Quick sync failed for {err.get('institution', 'unknown')}: {err['error']}")

        logger.info(f"Quick sync complete: {total_accounts} accounts updated, {len(errors)} errors")

    except Exception as e:
        logger.error(f"Quick sync failed: {e}")
    finally:
        db.close()


def daily_sync_job():
    """Job that runs to sync all institutions including transactions"""
    logger.info(f"Starting full sync at {datetime.now()}")

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
    # Run full sync daily at 6 AM
    scheduler.add_job(
        daily_sync_job,
        CronTrigger(hour=6, minute=0),
        id="daily_sync",
        name="Daily Financial Sync",
        replace_existing=True
    )

    # Full sync every 4 hours (transactions + balances)
    scheduler.add_job(
        daily_sync_job,
        CronTrigger(hour="*/4"),
        id="periodic_sync",
        name="Periodic Financial Sync (Full)",
        replace_existing=True
    )

    # Quick sync every hour (balances only - fast)
    # Runs at minutes 30 to offset from full syncs at the top of the hour
    scheduler.add_job(
        quick_sync_job,
        CronTrigger(minute=30),
        id="quick_sync",
        name="Hourly Balance Update (Quick)",
        replace_existing=True
    )

    scheduler.start()
    logger.info("Scheduler started - full sync every 4h, quick sync every hour")


def stop_scheduler():
    """Stop the scheduler"""
    scheduler.shutdown()
    logger.info("Scheduler stopped")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Running manual sync...")
    daily_sync_job()
