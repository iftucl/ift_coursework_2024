"""Team Ginkgo Coursework Two main module.

This module serves as the entry point for the application, providing a command-line
interface to interact with various functionalities of the system.
"""

from db import create_reports_with_indicators
from output import main as run_output_process


def menu():
    """Display the main menu options to the user.

    Prints a formatted menu with numbered options for different functionalities
    available in the system.
    """
    print("=== Menu ===")
    print("1. Initialize table structure")
    print("2. Run CSR report processing")
    print("3. Run all")
    print("0. Exit")


def main():
    """Main function that runs the application.

    Provides an interactive command-line interface where users can choose
    different operations to perform. The function runs in a loop until the
    user chooses to exit.

    The available operations are:
        1. Initialize database tables
        2. Process CSR reports
        3. Run both initialization and processing
        0. Exit the application
    """
    while True:
        menu()
        choice = input("Enter your choice: ").strip()

        if choice == "1":
            create_reports_with_indicators()
        elif choice == "2":
            run_output_process()
        elif choice == "3":
            create_reports_with_indicators()
            run_output_process()
        elif choice == "0":
            print("Exiting")
            break
        else:
            print("Invalid input. Please try again.")


if __name__ == "__main__":
    main()

