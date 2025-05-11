"""
This module provides a function to run a security scan on a specified source code directory using Bandit.

Bandit is a tool designed to find common security issues in Python code. This module uses the `poetry` package
to execute the Bandit scan on a specified directory (`modules/data_storage`).

Main function:
- `run_bandit_scan`: Executes Bandit on the source code directory to identify security issues.

To run this module:
- Execute it as the main program using the `if __name__ == "__main__":` block.
"""

import os

def run_bandit_scan():
    """
    Executes a security scan on the source code directory using Bandit.

    This function runs the Bandit tool on the `modules/data_storage` directory, scanning the Python source code
    for common security issues. It uses `poetry` to execute the scan.

    The Bandit scan helps identify potential security flaws, such as improper handling of inputs, hardcoded
    passwords, insecure cryptographic practices, and more.

    :return: None
    :rtype: None
    """
    # Specify the source code path to be scanned
    src_path = "modules/data_storage"
    
    # Use poetry to run Bandit scan
    os.system(f"poetry run bandit -r {src_path}")

if __name__ == "__main__":
    run_bandit_scan()
