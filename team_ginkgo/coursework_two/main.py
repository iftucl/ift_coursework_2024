from db import create_reports_with_indicators
from output import main as run_output_process


def menu():
    print("=== Menu ===")
    print("1. Initialize table structure")
    print("2. Run CSR report processing")
    print("3. Run all")
    print("0. Exit")


def main():
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

