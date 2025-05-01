Installation Guide
=================

This guide will help you set up the Team Ginkgo Coursework Two project locally.

Prerequisites
------------

Before installing the project, ensure you have the following installed:

- Python 3.13 or higher
- Poetry (Python package manager)
- PostgreSQL (for database functionality)
- Java (for PlantUML diagrams)

Installation Steps
----------------

1. Clone the repository:

   .. code-block:: bash

      git clone <repository-url>
      cd team_ginkgo_coursework_two

2. Install dependencies using Poetry:

   .. code-block:: bash

      poetry install

3. Set up the database:

   - Create a PostgreSQL database
   - Update the database configuration in the project settings
   - Run database migrations

4. Configure environment variables:

   Create a ``.env`` file in the project root with the following variables:

   .. code-block:: bash

      DATABASE_URL=postgresql://user:password@localhost:5432/dbname
      LOG_LEVEL=INFO
      API_KEY=your_api_key

5. Run database migrations:

   .. code-block:: bash

      poetry run alembic upgrade head

Verification
-----------

To verify the installation, run:

.. code-block:: bash

   poetry run pytest

If all tests pass, your installation is successful.

Troubleshooting
-------------

If you encounter any issues during installation:

1. Check Python version:

   .. code-block:: bash

      python --version

2. Verify Poetry installation:

   .. code-block:: bash

      poetry --version

3. Ensure PostgreSQL is running:

   .. code-block:: bash

      psql --version

4. Check Java installation:

   .. code-block:: bash

      java -version 