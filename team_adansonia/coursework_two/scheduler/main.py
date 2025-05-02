import sys
import os
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

# Add parent directory to import path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scheduler_test import say_hello  # now this works!

if __name__ == "__main__":
    scheduler = BlockingScheduler()
    scheduler.add_job(say_hello, CronTrigger(minute="*"))  # Run every minute

    try:
        print("Scheduler started. Press Ctrl+C to exit.")
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("Shutting down scheduler...")