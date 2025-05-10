System Architecture
===================

Key Steps
---------
   1. **Data Fetching**
       - Source: SQLite database, specifically the ``equity_static`` table
       - Fields: ``symbol, security, gics_sector, gics_industry``
       - Method: ``get_companies_from_db()`` function

   2. **Report Search**
       - API: Google Custom Search JSON API
       - Query Construction: ``{security} ESG CSR sustainability report filetype:pdf``
       - Error Handling: Catches ``Exception`` and truncates error messages for readability

   3. **File Download**
       - User Agent: Simulates browser requests (Mozilla/5.0)
       - Storage Path: ``b_pipeline/csr_reports/<region>/<country>/<industry>/<sector>/<company>/<year>``
       - Validation: Extracts year from URL using regex

   4. **Storage Layer**
       - **MinIO**:
          - Bucket Structure: Organized by geography and industry
          - Upload Method: Uses boto3's ``upload_file()``
       - **PostgreSQL**:
          - Table Schema: Includes ``company_name, year, file_path, minio_url`` fields
          - Deduplication: Implemented via ``check_if_report_exists()``

System Components
-----------------
    +-----------------------+---------------------------------+--------------------------------+
    |       Component       |           Description           |      Implementation/Config     |
    +-----------------------+---------------------------------+--------------------------------+
    |    **Data Source**    |     Stores company metadata     |     ``equity_static`` table    |
    +-----------------------+---------------------------------+--------------------------------+
    |   **Search Engine**   |    Finds CSR report PDF links   |  ``google_search()`` function  |
    |                       |                                 |           ``API_KEY``          |
    +-----------------------+---------------------------------+--------------------------------+
    |    | **Downloader**   | Downloads and validates PDFs    |   ``download_pdf()`` function  |
    |                       | Automatically creates directory |                                |
    +-----------------------+---------------------------------+--------------------------------+
    |   **Object Storage**  |           Stores PDFs           | ``upload_to_minio()`` function |
    +-----------------------+---------------------------------+--------------------------------+
    | **Metadata Database** |    Tracks report versions and   |     ``csr_metadata`` table     |
    |                       |         storage location        |                                |
    +-----------------------+---------------------------------+--------------------------------+

   Architecture Features
    ---------------------
       1. **Modular Design**  
           - Search, download, and storage modules are decoupled
           - Easy to replace ``google_search()`` with another search engine

       2. **Idempotency**  
           - Deduplication via database checks
           - Consistent naming conventions in MinIO

       3. **Observability**  
           - status logging in the console  
           - Success/failure tracking for critical operations

       4. **Extensibility**  
           - Reserved fields like ``gics_sector`` and ``region`` for future analytics
           - Can add ``requests.Session`` for connection pooling