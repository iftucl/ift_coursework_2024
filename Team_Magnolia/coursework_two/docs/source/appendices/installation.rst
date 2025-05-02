Installation
============
============

Appendix A: Installation Guide
This section outlines the steps required to install and configure the CSR extraction pipeline locally. The instructions assume a Unix-based environment with Docker and Python ≥ 3.10 installed.

.. raw:: html

    <table border="1" style="border-collapse: collapse;">
    <thead>
        <tr><th>Step</th><th>Action</th><th>Purpose</th></tr>
    </thead>
    <tbody>
        <tr><td>1</td><td>Clone the repository and navigate to the coursework_two directory</td><td>Initializes local development environment</td></tr>
        <tr><td>2</td><td>Install Poetry and Python ≥ 3.10</td><td>Manages virtual environments and dependencies</td></tr>
        <tr><td>3</td><td>Launch infrastructure services via docker compose up</td><td>Brings up MongoDB, MinIO, and PostgreSQL</td></tr>
        <tr><td>4</td><td>Install dependencies with poetry install --with dev</td><td>Includes runtime and developer toolchains</td></tr>
        <tr><td>5</td><td>Activate the virtual environment (poetry shell or prefix commands with poetry run)</td><td>Isolates dependencies from the system-wide Python</td></tr>
        <tr><td>6</td><td>Seed MinIO with PDF reports manually or via scraper</td><td>Provides raw inputs for the extraction pipeline</td></tr>
        <tr><td>7</td><td>Populate dim_companies via setup_collections module</td><td>Sets up indexing structures for company lookup</td></tr>
        <tr><td>8</td><td>Export the LLM API key as GROQ_API_KEY</td><td>Enables external LLM integration</td></tr>
        <tr><td>9</td><td>(Optional) Modify config/conf.yaml for endpoint customization</td><td>Supports bucket name or model override</td></tr>
    </tbody>
    </table>

Note: For scanned PDFs, enable GPU OCR in modules/extractor.py and install pytesseract with poppler.