"""
This module defines and manages the execution of a series of Python scripts in a data processing pipeline.

It includes functions for executing shell commands, logging the results, tracking completed modules,
and executing the pipeline with progress reporting. The pipeline logs progress and execution times
of individual modules, ensuring each module is executed only once.

Modules run by this pipeline:
- `create_table.py`
- `paragraph_extraction.py`
- `retry_failed_reports.py`
- `llm_analyse.py`
- `llm_standardize.py`
- `data_export.py`

Functions:
- `read_completed_modules`: Reads a list of completed modules from a file.
- `write_completed_module`: Appends a completed module to a record file.
- `run_command`: Executes a shell command and logs the result.
- `main`: Orchestrates the pipeline execution, including dependency installation, module execution, and logging.
"""

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

def read_completed_modules():
    """
    Reads the list of modules that have already been completed from a file.

    This function checks for a file containing the names of completed modules and returns
    a set of these module names. If the file does not exist, an empty set is returned.

    :return: A set of module names that have been completed.
    :rtype: set
    :raises FileNotFoundError: If the completed modules file is not found.
    """
    try:
        with open(completed_file_path, "r") as f:
            completed_modules = f.read().splitlines()
        return set(completed_modules)
    except FileNotFoundError:
        return set()

def write_completed_module(module):
    """
    Appends the name of a completed module to the record file.

    This function writes the provided module name to a file that tracks which modules
    have been executed. Each module name is written on a new line.

    :param module: The name of the module that has been completed.
    :type module: str
    :return: None
    :raises: Any exceptions raised during file operations.
    """
    with open(completed_file_path, "a") as f:
        f.write(module + "\n")

def run_command(command):
    """
    Executes a shell command and logs the result.

    This function runs the specified command in the shell, logging the start and success of the execution.
    If the command fails, the error is logged, and the script exits with a failure code.

    :param command: The shell command to execute.
    :type command: str
    :return: None
    :raises subprocess.CalledProcessError: If the command fails during execution.
    """
    try:
        logging.info(f"Starting command: {command}")
        subprocess.run(command, check=True, shell=True)
        logging.info(f"Successfully completed: {command}")
    except subprocess.CalledProcessError as e:
        logging.error(f"Command failed: {command}")
        logging.error(str(e))
        sys.exit(1)

def main():
    """
    Orchestrates the execution of the full data processing pipeline.

    This function installs the necessary dependencies, loads the list of completed modules,
    and iterates over a predefined set of modules to execute. It tracks the execution progress
    and logs each step. Each module is only executed once, and the completion is recorded.

    :return: None
    :raises: Any exceptions raised during the pipeline execution.
    """
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
