Usage Instructions
==================

1. **Run the extraction pipeline**:

   .. code-block:: bash

      poetry run python Main.py

   This will:
   - Connect to MinIO and stream CSR PDF reports  
   - Chunk each PDF into text blocks  
   - Query Deepseek API to extract indicator values  
   - Append results to `logs/final_output.csv`

2. **Post-processing & Data Cleaning**

   After extraction, clean, merge and load your CSR data:

   a. **Data Cleaning**: normalize and split values in the raw CSV:

      .. code-block:: bash

         poetry run python src/modules/output/data_cleaning.py

   b. **Metadata Export & Merge**: export `company_reports` and `company_static` tables from Postgres and merge:

      .. code-block:: bash

         poetry run python src/modules/output/reports_export.py

   c. **Database Load**: create schema/table and bulk-load the cleaned CSV into Postgres:

      .. code-block:: bash

         poetry run python src/modules/output/db_load.py

Troubleshooting Tips
--------------------

- **Deepseek API errors**:  
  • Verify `DEEPSEEK_API` in your `.env` is correct.  
  • Check your plan’s rate limits.  
- **MinIO connection issues**:  
  • Confirm `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY` and `MINIO_SECURE` in `.env`.  
- **Database connectivity**:  
  • Ensure Postgres is running and the `DB_*` credentials in `.env` match your instance.  
- **No indicators extracted**:  
  • Inspect `logs/final_log.txt` for parsing warnings or failures.  
