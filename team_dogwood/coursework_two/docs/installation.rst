Installation Guide
==================

To get started with the project, follow these steps:

1. **Clone the Repository**: If you haven’t already, clone the repository using Git.

   .. code-block:: bash

      git clone https://github.com/imanzaf/ift_coursework_2024.git

2. **Install Python and Poetry**:
   - Ensure you have Python installed. You can download it from https://python.org.
   - Install Poetry by following the official Poetry installation guide.

3. **Navigate to the Project Directory**: Move into the cloned repository directory.

   .. code-block:: bash

      cd team_dogwood/coursework_two

4. **Install Dependencies**: Use Poetry to install the project dependencies.

   .. code-block:: bash

      poetry install

5. **Set Up Environment Variables**: Create a `.env` file in the root directory and populate it with the required credentials.

   .. code-block:: bash

      cp .env.template .env

6. **Run the Project**: Use Poetry to run the main script.

   .. code-block:: bash

      poetry run python src/main.py

**Services**

The project uses the following services via Docker:

- MongoDB
- PostgreSQL
- MinIO

To start them:

.. code-block:: bash

   docker compose up

To stop them:

.. code-block:: bash

   docker compose down

**Usage Options (CLI)**

You can run the script in different modes:

- Run once:

  .. code-block:: bash

     poetry run python src/main.py --run-once

- Run immediately then schedule (default: monthly):

  .. code-block:: bash

     poetry run python src/main.py --run-now

- Set custom schedule:

  .. code-block:: bash

     poetry run python src/main.py --schedule weekly

- Combine flags:

  .. code-block:: bash

     poetry run python src/main.py --run-now --schedule weekly

**Usage Options (.env)**

You can configure scheduling and service credentials through the `.env` file:

1. Copy the template:

   .. code-block:: bash

      cp .env.template .env

2. Edit the file with your preferences and credentials.

3. Run without CLI flags:

   .. code-block:: bash

      poetry run python src/main.py

**Running Unit Tests**

To run unit tests:

.. code-block:: bash

   poetry run pytest

**Running Pre-commit Hooks**

Install pre-commit hooks:

.. code-block:: bash

   poetry run pre-commit install

Run all hooks manually:

.. code-block:: bash

   poetry run pre-commit run --all-files
