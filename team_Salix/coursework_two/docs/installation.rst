CSR Indicators Data Product - Installation Guide
=========================================

This guide will help you set up the CSR Indicators Data Product locally.

Prerequisites
------------

- Python 3.9 or higher
- Poetry (Python package manager)
- PostgreSQL 12 or higher
- Git

Installation Steps
----------------

1. Clean up old Docker containers (if any):

   .. code-block:: bash

      docker stop $(docker ps -aq) 2>/dev/null
      docker rm $(docker ps -aq) 2>/dev/null
      docker network prune -f
      docker volume prune -f
      docker system prune -a -f

2. Verify Docker & Poetry installation:

   .. code-block:: bash

      docker --version
      poetry --version

3. Start Docker services:

   .. code-block:: bash

      docker compose up --build -d

4. Install Python dependencies:

   .. code-block:: bash

      cd coursework_two
      rm -rf .venv
      poetry env remove --all
      poetry install --no-root

5. Set up environment variables:

   Create a ``.env`` file in the coursework_two directory with the following variables:

   .. code-block:: text

      # Database Configuration
      DB_HOST=localhost
      DB_PORT=5439
      DB_NAME=fift
      DB_USER=postgres
      DB_PASSWORD=postgres

      # API Keys
      XAI_API_KEY=your_xai_api_key_here
      DEEPSEEK_API_KEY=your_deepseek_api_key_here

      # File Paths
      JSON_PATH=config/ref.json
      DOWNLOAD_PATH=pipeline1/result/csr_reports

6. Verify Database Connection:

   - Ensure you can connect to the pre-configured PostgreSQL database
   - Test the connection using the provided credentials in ``coursework_two/.env``
   - Verify access to the ``csr_reporting`` schema

Verification
-----------

To verify the installation, run the test suite:

.. code-block:: bash

   poetry run pytest

Troubleshooting
--------------

Common Issues
~~~~~~~~~~~~

1. Database Connection Issues
   - Ensure PostgreSQL is running
   - Verify database credentials in ``.env``
   - Check database permissions

2. API Key Issues
   - Verify API keys are correctly set in ``.env``
   - Check API key permissions and quotas

3. Poetry Installation Issues
   - Ensure Poetry is installed correctly
   - Try ``poetry update`` if dependency resolution fails

Getting Help
-----------

If you encounter any issues not covered in this guide, please:

1. Check the :doc:`usage` guide for common operations
2. Review the :doc:`architecture` documentation
3. Open an issue on the project's GitHub repository 