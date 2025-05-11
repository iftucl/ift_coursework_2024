"""
This module provides a function to run a security check on the project dependencies using Safety.

Safety is a tool for checking Python dependencies for known security vulnerabilities. This module uses `poetry`
to execute the Safety check command.

Main function:
- `run_safety_check`: Executes Safety to check for known security issues in the project dependencies.

To run this module:
- Execute it as the main program using the `if __name__ == "__main__":` block.
"""

import os

def run_safety_check():
    """
    Executes a security check on the project dependencies using Safety.

    This function runs the Safety tool, which checks the project's dependencies for known security vulnerabilities.
    The check is executed using `poetry` as the package manager to run the Safety command.

    :return: None
    :rtype: None
    """
    os.system("poetry run safety check")

if __name__ == "__main__":
    run_safety_check()
