"""
Pipeline Scheduler for CSR Report Collection System

This script manages the scheduling of all pipeline executions using APScheduler.
It supports flexible execution frequencies (daily, weekly, monthly) and can be
configured via command line arguments or a YAML configuration file.

Usage:
    python scheduler.py --frequency daily
    python scheduler.py --frequency weekly
    python scheduler.py --frequency monthly
    python scheduler.py --config config/scheduler_config.yaml
"""

import argparse
import logging
import os

import yaml
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("logssch/scheduler.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


def run_pipeline1():
    """Execute Pipeline 1: PDF file download and storage"""
    try:
        logger.info("Starting Pipeline 1: PDF Download and Storage")
        os.system("python pipeline1/modules/main.py")
        logger.info("Pipeline 1 completed successfully")
    except Exception as e:
        logger.error(f"Pipeline 1 failed: {str(e)}")


def run_pipeline2():
    """Execute Pipeline 2: PDF text extraction and preprocessing"""
    try:
        logger.info("Starting Pipeline 2: PDF Text Extraction")
        os.system("python pipeline2/modules/modelv2.py")
        logger.info("Pipeline 2 completed successfully")
    except Exception as e:
        logger.error(f"Pipeline 2 failed: {str(e)}")


def run_pipeline3():
    """Execute Pipeline 3: ESG metrics extraction and database writing"""
    try:
        logger.info("Starting Pipeline 3: ESG Metrics Extraction")
        os.system("python pipeline3/modules/write_to_db.py")
        os.system("python pipeline3/modules/write_lineage.py")
        logger.info("Pipeline 3 completed successfully")
    except Exception as e:
        logger.error(f"Pipeline 3 failed: {str(e)}")


def run_pipeline4():
    """Execute Pipeline 4: Data visualization dashboard"""
    try:
        logger.info("Starting Pipeline 4: Dashboard Update")
        os.system("streamlit run pipeline4/modules/dashboard.py")
        logger.info("Pipeline 4 started successfully")
    except Exception as e:
        logger.error(f"Pipeline 4 failed: {str(e)}")


def load_config(config_path):
    """Load scheduling configuration from YAML file"""
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def get_cron_expression(frequency):
    """Return cron expression based on frequency"""
    cron_expressions = {
        "daily": "0 0 * * *",  # Run at midnight every day
        "weekly": "0 0 * * 0",  # Run at midnight on Sunday
        "monthly": "0 0 1 * *",  # Run at midnight on the 1st of each month
    }
    return cron_expressions.get(frequency)


def setup_scheduler(frequency=None, config_path=None):
    """Set up and start the scheduler"""
    scheduler = BlockingScheduler()

    if config_path and os.path.exists(config_path):
        # Load scheduling settings from config file
        config = load_config(config_path)
        for pipeline, settings in config["pipelines"].items():
            if settings["enabled"]:
                trigger = CronTrigger.from_crontab(settings["cron"])
                pipeline_func = globals()[f"run_pipeline{pipeline[-1]}"]
                scheduler.add_job(
                    pipeline_func,
                    trigger=trigger,
                    id=f"pipeline{pipeline[-1]}",
                    name=settings["name"],
                )
                logger.info(f"Scheduled {settings['name']} with cron: {settings['cron']}")
    else:
        # Set uniform scheduling frequency using command line arguments
        cron_expr = get_cron_expression(frequency)
        for i in range(1, 5):
            pipeline_func = globals()[f"run_pipeline{i}"]
            scheduler.add_job(
                pipeline_func,
                trigger=CronTrigger.from_crontab(cron_expr),
                id=f"pipeline{i}",
                name=f"Pipeline {i}",
            )
        logger.info(f"All pipelines scheduled with frequency: {frequency}")

    return scheduler


def main():
    """Main function: parse arguments and start the scheduler"""
    parser = argparse.ArgumentParser(description="CSR Pipeline Scheduler")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--frequency",
        choices=["daily", "weekly", "monthly"],
        help="Execution frequency for all pipelines",
    )
    group.add_argument("--config", help="Path to YAML configuration file")

    args = parser.parse_args()

    try:
        # Ensure log directory exists
        os.makedirs("logs", exist_ok=True)

        # Set up and start the scheduler
        scheduler = setup_scheduler(frequency=args.frequency, config_path=args.config)

        logger.info("Scheduler starting...")
        scheduler.start()
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user")
    except Exception as e:
        logger.error(f"Scheduler error: {str(e)}")


if __name__ == "__main__":
    main()
