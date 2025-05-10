CSR Indicators Data Product - Usage Guide
===================================

This guide explains how to use the CSR Indicators Data Product.

Running the Pipeline
------------------

The system can be run in two modes:

1. Manual Execution
~~~~~~~~~~~~~~~~~

Run each pipeline individually:

.. code-block:: bash

   # Pipeline 1: Data Availability Check
   poetry run python pipeline1/modules/main.py
   poetry run python pipeline1/modules/pdf_checker.py
   poetry run python pipeline1/modules/process_problematic.py

   # Pipeline 2: Content Extraction
   poetry run python pipeline2/modules/modelv2.py

   # Pipeline 3: Storage Implementation
   poetry run python pipeline3/modules/write_to_db.py
   poetry run python pipeline3/modules/write_lineage.py

   # Pipeline 4: Visualization
   poetry run streamlit run pipeline4/modules/dashboard.py

2. Scheduled Execution
~~~~~~~~~~~~~~~~~~~~

Use the scheduler to run pipelines automatically:

.. code-block:: bash

   poetry run python scheduler.py

Configuration
-----------

Environment Configuration
~~~~~~~~~~~~~~~~~~~~~~~

Create a ``.env`` file in the project root with the following variables:

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

Scheduler Configuration
~~~~~~~~~~~~~~~~~~~~

The scheduler can be configured using the ``config/scheduler_config.yaml`` file:

.. code-block:: yaml

   pipelines:
     pipeline1:
       frequency: daily
       time: "00:00"
     pipeline2:
       frequency: daily
       time: "01:00"
     pipeline3:
       frequency: daily
       time: "02:00"
     pipeline4:
       frequency: daily
       time: "03:00"

Dashboard Usage
------------

The dashboard provides interactive visualization of CSR indicators:

1. Indicators Overview
   - Filter data by company and year
   - View detailed CSR metrics
   - Generate trend charts

2. Data Lineage
   - View data flow information
   - Track processing steps
   - Analyze data quality

Troubleshooting
-------------

Common Issues
~~~~~~~~~~~

1. Data Availability Issues
   - Check report accessibility
   - Verify PDF format
   - Check file permissions

2. Content Extraction Issues
   - Verify API key validity
   - Check API rate limits
   - Ensure PDF text is extractable

3. Database Issues
   - Verify database connection
   - Check schema permissions
   - Ensure data format compatibility

4. Dashboard Issues
   - Check database connection
   - Verify data availability
   - Clear browser cache if needed

Getting Help
----------

For additional help:

1. Check the :doc:`installation` guide
2. Review the :doc:`architecture` documentation
3. Open an issue on GitHub 