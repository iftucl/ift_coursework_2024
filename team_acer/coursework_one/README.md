CSR Report Extraction Pipeline

This project extracts, processes, and stores Corporate Social Responsibility (CSR) reports using Google Search API, Selenium, and BeautifulSoup to retrieve reports, validate them, and store metadata in PostgreSQL and the reports in MinIO.

Setup & Installation

1. Start Docker Services

Ensure Docker is installed and running. Navigate to the directory containing docker-compose.yml and execute:

 docker-compose up --build -d

This will set up PostgreSQL, MinIO, and any other required services.

2. Install Poetry & Dependencies

If Poetry is not installed, install it first:

pip install poetry 

Now, install the dependencies:

 poetry install



Running the Extraction Pipeline

🔹 Option 1: Run Manually

Navigate to the project root and execute:

 poetry run python -m a_pipeline.modules.extracting_csr_reports.fetch_csr_reports

This will start processing CSR reports one by one.

🔹 Option 2: Run in Background with APScheduler

To automate report extraction using a scheduler:

 poetry run python -m a_pipeline.modules.scheduler.scheduler_script

This runs in the background, checking for new reports at regular intervals.


Running FastAPI

To start the FastAPI server, run:

 poetry run uvicorn a_pipeline.modules.api.app:app --host 0.0.0.0 --port 8080 --reload

Access API documentation at: http://localhost:8080/docs

🛑 Prevent Laptop from Sleeping ⚡️

Since the extraction process takes a long time, prevent your laptop from sleeping:

🔹 macOS

 caffeinate -i -t 36000  # Keeps the system awake for 10 hours

🔹 Windows

 powercfg /change monitor-timeout-ac 0
 powercfg /change standby-timeout-ac 0

🔹 Linux

 xset s off -dpms  # Disables screen timeout & power management

Troubleshooting

Google API Rate Limit Exceeded

Wait a few minutes before retrying or use a different API key.

No Reports Found

Check if the company name is formatted correctly.

Database Connection Issues

Ensure PostgreSQL is running: docker ps

Notes

The script processes one company at a time, one year at a time, ensuring no conflicts.

Results are stored in PostgreSQL (metadata) & MinIO (reports).

Invalid reports (e.g., incorrect year, no CSR content) are discarded.

Happy extracting!

