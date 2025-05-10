"""
Main script to schedule and run the PDF parser, query tool, and metric storage script using APScheduler.
"""

import argparse
import asyncio
import sys
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
from loguru import logger
# Ensure src is in path for import
import os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.extract.parse import main as parse_main
from src.extract.query import main as query_main
from config.schedule import schedule_settings


def get_cron_trigger(schedule: str) -> CronTrigger:
    """
    Return a CronTrigger for the given schedule string.
    """
    if schedule == "weekly":
        # Run at midnight every Monday
        return CronTrigger(day_of_week='mon', hour=0, minute=0)
    elif schedule == "monthly":
        # Run at midnight on the 1st of every month
        return CronTrigger(day=1, hour=0, minute=0)
    elif schedule == "quarterly":
        # Run at midnight on the 1st of Jan, Apr, Jul, Oct
        return CronTrigger(month='1,4,7,10', day=1, hour=0, minute=0)
    elif schedule == "yearly":
        # Run at midnight on Jan 1st
        return CronTrigger(month=1, day=1, hour=0, minute=0)
    else:
        raise ValueError(f"Unknown schedule: {schedule}")


def run_parse_and_query():
    """
    Run the async main() from parse.py, then the main() from query.py.
    """
    logger.info(f"Running parse.main() at {datetime.now().isoformat()}")
    try:
        asyncio.run(parse_main())
    except Exception as e:
        logger.error(f"Error running parse.main(): {e}")
        return
    logger.info(f"Running query.main() at {datetime.now().isoformat()}")
    try:
        query_main()
    except Exception as e:
        logger.error(f"Error running query.main(): {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Schedule and run the PDF extraction script with APScheduler."
    )
    parser.add_argument(
        "--schedule",
        choices=["monthly", "weekly", "quarterly", "yearly"],
        default=schedule_settings.FREQUENCY,
        help="How often to run the script (default: monthly)."
    )
    parser.add_argument(
        "--run-now",
        action="store_true",
        default=schedule_settings.RUN_NOW,
        help=f"Run the script immediately before scheduling. Default: {schedule_settings.RUN_NOW}"
    )
    parser.add_argument(
        "--run-once",
        action="store_true",
        default=schedule_settings.RUN_ONCE,
        help=f"Run the script only once and exit. Default: {schedule_settings.RUN_ONCE}"
    )
    args = parser.parse_args()

    if args.run_once:
        run_parse_and_query()
        # Do not schedule, exit after running once
        logger.info("Run-once mode enabled. Exiting after single run.")
        return

    if args.run_now:
        run_parse_and_query()

    scheduler = BlockingScheduler()
    trigger = get_cron_trigger(args.schedule)
    scheduler.add_job(run_parse_and_query, trigger)
    logger.info(f"Scheduled parse.main() and query.main() to run {args.schedule}ly. Press Ctrl+C to exit.")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped.")


if __name__ == "__main__":
    main()