import threading
import subprocess


def run_wyy(script_name: str) -> None:
    """Run a Python script and report the result."""
    result = subprocess.run(['python', script_name])
    msg = "succeeded" if result.returncode == 0 else f"failed (code {result.returncode})"
    print(f"Script '{script_name}' {msg}.")


def main():
    while True:
        print("Run all processes (create database in PostgreSQL → scrap url → storage url to PostgreSQL → download reports → upload to Minio)")

        run_wyy('modules/database.py')

        run_wyy('modules/scraping.py')

        run_wyy('modules/URL_db.py')

        t1 = threading.Thread(target=lambda: subprocess.run(['python', 'KafkaConsumer.py'])).start()
        t2 = threading.Thread(target=lambda: subprocess.run(['python', 'KafkaProducer.py'])).start()

        t1.start()
        t2.start()

        t1.join()
        t2.join()

        print("All processes completed.")


if __name__ == "__main__":
    main()
