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

Now, install the dependencies. Navigate to the directory containing pyproject.toml and execute:

 poetry install

3. Checking and Creating the csr_metadata Table in pgAdmin
Step 1: Log in to pgAdmin
 1. Open pgAdmin and log in using the credentials defined in docker-compose.yml:
        Email: admin@admin.com
        Password: root

Step 2: Add a New Server
 1. In pgAdmin, right-click on "Servers" in the left panel and select "Create" → "Server".

 2. Under the General tab:

        Name: Postgres_DB (or any name of your choice)

 3. Under the Connection tab:

        Host name/address: postgres_db
        Port: 5432
        Maintenance database: fift
        Username: postgres
        Password: postgres
        Click "Save" to create the connection.

Step 3: Verify if the csr_metadata Table Exists
 1. Expand "Servers" → "Postgres_DB".
 2. Navigate to "Databases" → "fift" → "Schemas" → "public" → "Tables".
 3. Check if csr_metadata exists in the list.

Step 4: Create csr_metadata Table (If It Does Not Exist)
If the table does not exist, open the Query Tool and execute the following SQL command:

CREATE TABLE IF NOT EXISTS public.csr_metadata (
    id SERIAL PRIMARY KEY,
    symbol TEXT NOT NULL,
    security TEXT NOT NULL,
    year INT NOT NULL,
    region TEXT NOT NULL,
    country TEXT NOT NULL,
    sector TEXT NOT NULL,
    industry TEXT NOT NULL,
    minio_url TEXT NOT NULL,
    UNIQUE(symbol, year)  -- Prevents duplicate entries for the same company & year
);

Running the Extraction Pipeline

Navigate to the a_pipeline:

🔹 Option 1: Run Manually

Navigate (cd) to the a_pipeline:

 poetry run python -m modules.extracting_csr_reports.fetch_csr_reports

This will start processing CSR reports one by one.

🔹 Option 2: Run in Background with APScheduler

To automate report extraction using a scheduler:

 poetry run python -m modules.scheduler.scheduler_script

This runs in the background, checking for new reports at regular intervals.


Running FastAPI

To start the FastAPI server, run:

poetry run uvicorn modules.fast_api.app:app --host 0.0.0.0 --port 8080 --reload

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

Sometimes it is due to a slow interent connection since a timeout has been used

Database Connection Issues

Ensure PostgreSQL is running: docker ps

Notes

The script processes one company at a time, one year at a time, ensuring no conflicts.

Results are stored in PostgreSQL (metadata) & MinIO (reports).

Invalid reports (e.g., incorrect year, no CSR content) are discarded.

Happy extracting!