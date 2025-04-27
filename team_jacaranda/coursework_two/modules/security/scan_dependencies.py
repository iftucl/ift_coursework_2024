import os

def run_safety_check():
    os.system("poetry run safety check")

if __name__ == "__main__":
    run_safety_check()

