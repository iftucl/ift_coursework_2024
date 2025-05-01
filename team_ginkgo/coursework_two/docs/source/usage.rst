Usage Guide
===========

This guide explains how to use the Team Ginkgo Coursework Two project.

Running the Pipeline
------------------

To run the main pipeline:

.. code-block:: bash

   poetry run python main.py

Configuration
------------

The project can be configured through:

1. Environment variables (in ``.env`` file)
2. Configuration files in the ``config`` directory
3. Command-line arguments

Troubleshooting
--------------

Common Issues and Solutions
~~~~~~~~~~~~~~~~~~~~~~~~~

1. Database Connection Issues
   - Verify database credentials in ``.env``
   - Check if PostgreSQL is running
   - Ensure database exists and is accessible

2. Dependency Issues
   - Run ``poetry install`` to ensure all dependencies are installed
   - Check Python version compatibility

3. API Issues
   - Verify API endpoints are correctly configured
   - Check network connectivity
   - Ensure required API keys are set

Logging
-------

The project uses Python's built-in logging module. Logs can be found in:

- ``logs/app.log`` for application logs
- ``logs/error.log`` for error logs

To change log levels, modify the logging configuration in the project settings. 