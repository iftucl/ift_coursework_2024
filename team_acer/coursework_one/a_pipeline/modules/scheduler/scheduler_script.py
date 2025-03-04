from apscheduler.schedulers.background import BackgroundScheduler
from modules.extracting_csr_reports.fetch_csr_reports import fetch_csr_reports
import logging
import time
import atexit

def _init_(self, name, age):
    self.name = name
    self.age = age

# Logging setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Define scheduled task
def scheduled_task():
    logging.info("🔄 Running scheduled CSR report extraction...")
    fetch_csr_reports()
    logging.info("✅ CSR report extraction completed.")

# Initialise and start APScheduler
scheduler = BackgroundScheduler()
scheduler.add_job(scheduled_task, "interval", days=7)  # Run every 7 days (adjust as needed)
scheduler.start()
logging.info("🚀 APScheduler started! Running in the background...")

# Ensure scheduler shuts down gracefully on exit
atexit.register(lambda: scheduler.shutdown(wait=False))

# Keep the script running
if __name__ == "__main__":
    try:
        while True:
            time.sleep(60)  # Prevents script from exiting
    except (KeyboardInterrupt, SystemExit):
        logging.info("❌ Scheduler stopped.")