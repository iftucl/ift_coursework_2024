Usage Instructions
==================

Running the Pipeline
--------------------

1. Fetch CSR Reports:

   .. code-block:: bash

      python fetch_csr_reports.py

   This will:
   - Query company data from SQLite
   - Search Google for PDF reports
   - Download valid reports to local directory

2. Upload to MinIO:

   .. code-block:: bash

      python store_minio.py

   This will:
   - Upload PDFs to MinIO bucket
   - Store metadata in PostgreSQL

3. Upload to postgres:

   .. code-block:: bash

      python store_postgres.py

   This will: 
   - Store metadata in PostgreSQL