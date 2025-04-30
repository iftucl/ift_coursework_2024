# Team Dogwood: Coursework Two

```
           &&& &&  & &&
       && &\/&\|& ()|/ @, &&                ==========================
       &\/(/&/&||/& /_/)_&/_&              ║     TEAM DOGWOOD      ║
    &() &\/&|()|/&\/ '%" & ()              ║=======================║
    &_\/&_/&&&|&&-&&--%---&_/_&            ║   Coursework Two     ║
    &&   && & &| &| /& & % ()& /&&         ==========================
     ()&_---()&\&\|&&-&&--%---()~
         &&     \|||           
                 |||           
                 |||           
                 |||           
               ,|'''|,         
               ||   ||         

```

## Project Dependencies

This project uses [Poetry](https://python-poetry.org/) for dependency management and environment setup. Assuming you have poetry installed, use the below commands to set up your environment.

1. **Install dependencies**:

   From the `team_dogwood/coursework_two` directory, run:

   ```bash
   poetry install
   ```

2. **Activate the Poetry environment**:

   ```bash
   poetry shell
   ```

<br><br>
Additionally, three database services are used for this project, namely: MongoDB, PostgreSQL, and MinIO. All three services are spun up using docker containers. No change to the `docker-compose.yml` in the root directory should be needed in order to successfully run this product.

**Before starting the services, ensure you have copied `.env.template` to `.env` and updated it with the correct database and service credentials for your environment.**

To start all services, run the below command from the root directory of the repository:

```bash
docker compose up
```

To stop the services, use:

```bash
docker compose down
<br>
```

<br><br>

## Usage Instructions

### Running or Scheduling the script
The main script for this coursework is located at `src/main.py`. 
The main script looks for company reports, parses them for metrics, and stores these metrics in PostgreSQL.

You can run the main script once, run it immediately and then schedule future runs, or schedule it to run at regular intervals using built-in options.

**Usage options: CLI**

- To run the script once and exit:
  ```bash
  poetry run python src/main.py --run-once
  ```

- To run the script immediately and then continue on a schedule (default: monthly):
  ```bash
  poetry run python src/main.py --run-now
  ```

- To specify a schedule (choose one: monthly, weekly, quarterly, yearly):
  ```bash
  poetry run python src/main.py --schedule weekly
  ```

You can combine options as needed. For example, to run immediately and then schedule weekly:
  ```bash
  poetry run python src/main.py --run-now --schedule weekly
  ```

<br>

**Usage Options: .env**

The main script and supporting modules require environment variables (such as database connection details) to be set in a `.env` file.

1. Copy the provided template to create your own environment file:
   ```bash
   cp .env.template .env
   ```
2. Edit `.env` to provide the correct values for your scheduling preferences.
3. Run the main script without specifying any CLI args:
  ```bash
  poetry run python src/main.py
  ```

The script will automatically load variables from `.env` when run.


<br><br>

### Running Unit Tests

To run the unit tests, run the following command in the `team_dogwood/coursework_two` directory:
```bash
poetry run pytest
```

<br>

### Running Pre-commit Hooks

This project uses [pre-commit](https://pre-commit.com/) to maintain code quality and consistency.

**To install the pre-commit hooks:**
```bash
poetry run pre-commit install
```

**To run all pre-commit hooks manually on all files:**
```bash
poetry run pre-commit run --all-files
```

It is recommended to run the hooks before committing code to ensure all checks pass.
