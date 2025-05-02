## Frontend Tests

To run all frontend-related tests with coverage:

# Method one:
Run "test_app.py, test_index_css.py, test_index_js.py, test_tailwind_config.py" one by one.

# Method two:
```bash
# Make sure Poetry is installed:
# https://python-poetry.org/docs/#installation

# Make sure the version of Python is above 3.10
# https://www.python.org/downloads/

cd coursework_two
poetry run pytest test/frontend/ --cov
