import sys
import os
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

# Add parent directory to import path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from main import main  # now this works!

if __name__ == "__main__":
    scheduler = BlockingScheduler()
    scheduler.add_job(main, CronTrigger(day=1, hour=0, minute=0))  # Run every minute

    try:
        print("Scheduler started. Press Ctrl+C to exit.")
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("Shutting down scheduler...")