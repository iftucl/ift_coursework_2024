import subprocess
import logging
import sys
import time
from tqdm import tqdm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("pipeline.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

# Module scripts located in the current folder
modules = [
    "create_table.py",
    "paragraph_extraction.py",
    "retry_failed_reports.py",
    "llm_analyse.py",
    "llm_standardize.py",
    "data_export.py",
]

# Read completed modules from file
def read_completed_modules():
    try:
        with open("completed_modules.txt", "r") as f:
            completed_modules = f.read().splitlines()
        return set(completed_modules)
    except FileNotFoundError:
        return set()

# Write completed module to file
def write_completed_module(module):
    with open("completed_modules.txt", "a") as f:
        f.write(module + "\n")

def run_command(command):
    """Run shell command and handle exceptions"""
    try:
        logging.info(f"Starting command: {command}")
        subprocess.run(command, check=True, shell=True)
        logging.info(f"Successfully completed: {command}")
    except subprocess.CalledProcessError as e:
        logging.error(f"Command failed: {command}")
        logging.error(str(e))
        sys.exit(1)

def main():
    logging.info("Starting the full pipeline for the data_storage module")

    # Install dependencies (only needed once)
    run_command("poetry install")

    # Get the list of completed modules from previous runs
    completed_modules = read_completed_modules()

    # Execute modules sequentially, record duration and show progress bar
    with tqdm(total=len(modules), desc="🧩 Progress", ncols=80) as pbar:
        for module in modules:
            # Skip the module if it's already completed
            if module in completed_modules:
                logging.info(f"Module {module} has already been completed, skipping...")
                pbar.update(1)
                continue
            
            cmd = f"poetry run python modules/data_storage/{module}"
            start_time = time.time()
            run_command(cmd)
            elapsed_time = time.time() - start_time
            logging.info(f"Execution time for module {module}: {elapsed_time:.2f} seconds")

            # Mark the module as completed
            write_completed_module(module)
            pbar.update(1)

    logging.info("data_storage module execution completed!")

if __name__ == "__main__":
    main()
