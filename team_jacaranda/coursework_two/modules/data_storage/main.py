import subprocess
import logging
import sys
import time
import os
from tqdm import tqdm

# Get the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Define paths for log and completed modules file
log_file_path = os.path.join(SCRIPT_DIR, "pipeline.log")
completed_file_path = os.path.join(SCRIPT_DIR, "completed_modules.txt")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file_path),
        logging.StreamHandler(sys.stdout)
    ]
)

# List of module scripts to run
modules = [
    "create_table.py",
    "paragraph_extraction.py",
    "retry_failed_reports.py",
    "llm_analyse.py",
    "llm_standardize.py",
    "data_export.py",
]

# Read list of completed modules from file
def read_completed_modules():
    try:
        with open(completed_file_path, "r") as f:
            completed_modules = f.read().splitlines()
        return set(completed_modules)
    except FileNotFoundError:
        return set()

# Append a completed module name to the record file
def write_completed_module(module):
    with open(completed_file_path, "a") as f:
        f.write(module + "\n")

# Run a shell command and log the result
def run_command(command):
    try:
        logging.info(f"Starting command: {command}")
        subprocess.run(command, check=True, shell=True)
        logging.info(f"Successfully completed: {command}")
    except subprocess.CalledProcessError as e:
        logging.error(f"Command failed: {command}")
        logging.error(str(e))
        sys.exit(1)

# Main pipeline execution
def main():
    logging.info("Starting the full pipeline for the data_storage module")

    # Install dependencies (only needed once)
    run_command("poetry install")

    # Load previously completed modules
    completed_modules = read_completed_modules()

    # Run each module in order, tracking progress and time
    with tqdm(total=len(modules), desc="🧩 Progress", ncols=80) as pbar:
        for module in modules:
            # Skip modules that were already completed
            if module in completed_modules:
                logging.info(f"Module {module} has already been completed, skipping...")
                pbar.update(1)
                continue

            cmd = f"poetry run python modules/data_storage/{module}"
            start_time = time.time()
            run_command(cmd)
            elapsed_time = time.time() - start_time
            logging.info(f"Execution time for module {module}: {elapsed_time:.2f} seconds")

            # Record completion of the module
            write_completed_module(module)
            pbar.update(1)

    logging.info("data_storage module execution completed!")

if __name__ == "__main__":
    main()
