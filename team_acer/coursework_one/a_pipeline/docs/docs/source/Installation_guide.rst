Installation Guide
==================

Prerequisites
-------------
- Python 3.8+
- PostgreSQL 13+
- MinIO Server
- Google API Key

Steps
-----

1. Clone the repository:

   .. code-block:: bash

      git clone https://github.com/S09aif/Coursework-1-for-Big-Data---Group-2-Acer-
      cd Database/SQL

2. Install dependencies:

   .. code-block:: bash

      pip install -r requirements.txt

3. Configure environment variables:

   Create a `.env` file with:

   .. code-block:: text

      # PostgreSQL
      DB_HOST=localhost
      DB_PORT=5438
      DB_NAME=fift
      DB_USER=postgres
      DB_PASSWORD=postgres

      # MinIO
      MINIO_ENDPOINT=http://localhost:9000
      MINIO_ACCESS_KEY=ift_bigdata
      MINIO_SECRET_KEY=minio_password

4. Initialize databases:
   - Create SQL tables using `Equity.db`
   - Run MinIO server with bucket `csr-reports`