"""
scheduler.py

This script sets up scheduled execution of main.py at a specified frequency
(daily, weekly, or monthly) using APScheduler. The scheduling frequency
is passed via a command-line argument.

Usage:
    poetry run python scheduler.py --frequency daily
    poetry run python scheduler.py --frequency weekly
    poetry run python scheduler.py --frequency monthly
"""

from apscheduler.schedulers.blocking import BlockingScheduler
import subprocess
import argparse
import sys

def run_main(frequency):
    """
    Executes the main.py script with the given frequency as an argument.

    Args:
        frequency (str): The scheduling frequency ('daily', 'weekly', or 'monthly').

    Returns:
        None
    """
    print(f"Running main.py with frequency: {frequency}")
    subprocess.run(["python", "main.py", "--frequency", frequency])

def schedule_job(frequency):
    """
    Schedules the execution of main.py at the specified frequency using APScheduler.

    Args:
        frequency (str): The scheduling frequency. Must be one of:
                         'daily'   → every day at 06:00
                         'weekly'  → every Monday at 06:00
                         'monthly' → the 1st day of each month at 06:00

    Raises:
        SystemExit: If an unsupported frequency is provided.

    Returns:
        None
    """
    scheduler = BlockingScheduler()

    if frequency == "daily":
        scheduler.add_job(lambda: run_main("daily"), trigger="cron", hour=6, minute=0)
    elif frequency == "weekly":
        scheduler.add_job(lambda: run_main("weekly"), trigger="cron", day_of_week='mon', hour=6, minute=0)
    elif frequency == "monthly":
        scheduler.add_job(lambda: run_main("monthly"), trigger="cron", day=1, hour=6, minute=0)
    else:
        print(f"Unsupported frequency: {frequency}")
        sys.exit(1)

    print(f"Scheduler started for '{frequency}' mode.")
    scheduler.start()

if __name__ == "__main__":
    """
    Parses command-line arguments and starts the scheduler for the selected frequency.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--frequency", choices=["daily", "weekly", "monthly"], required=True, help="Set the scheduling frequency.")
    args = parser.parse_args()

    schedule_job(args.frequency)
