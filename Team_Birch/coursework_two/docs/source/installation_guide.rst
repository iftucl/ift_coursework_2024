Installation Guide
==================

To set up this project locally:

1. Clone the repository:

   .. code-block:: bash

      git clone git clone https://github.com/Boissek123/coursework_two.git
      cd coursework_two

2. Install Poetry (if not already installed):

   .. code-block:: bash

      curl -sSL https://install.python-poetry.org | python3 -

3. Install dependencies:

   .. code-block:: bash

      poetry install

4. Create a `.env` file with the following variables:

   .. code-block:: text

      DEEPSEEK_API=your_deepseek_api_key
      
      MINIO_ENDPOINT=minio:9000
      MINIO_ACCESS_KEY=ift_bigdata
      MINIO_SECRET_KEY=minio_password
      MINIO_SECURE=false
      
      DB_NAME=fift
      DB_USER=postgres
      DB_PASSWORD=postgres
      DB_HOST=postgres
      DB_PORT=5439
      SCHEMA_NAME=csr_reporting
      TABLE_NAME=company_indicators

5. Run the extraction pipeline:

   .. code-block:: bash

      poetry run python Main.py

6. Database & Post-processing

   After extraction, three CSV-based scripts handle post-processing:

   - Data Cleaning ((`data_cleaning.py`)): cleans and reshapes raw CSR indicators CSV:

      .. code-block:: bash

         poetry run python src/modules/output/data_cleaning.py

   - Metadata Export & Merge ((`reports_export.py`)): exports and merges (`company_reports`) and (`company_static`) from Postgres:

      .. code-block:: bash

         poetry run python src/modules/output/reports_export.py

   - Postgres Load ((`db_load.py`)): creates schema/table and bulk-loads (`csr_indicators.csv`):

      .. code-block:: bash

         poetry run python src/modules/output/db_load.py

Once complete, the cleaned and validated CSR indicator data will be available in the (`csr_reporting.company_indicators`) table in your Postgres database.