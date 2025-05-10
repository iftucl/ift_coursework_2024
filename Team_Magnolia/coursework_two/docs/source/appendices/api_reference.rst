Api Reference
=============
=============

Appendix C: API Reference
The following API functions constitute the internal interface of the pipeline. These are derived from public docstrings using pydoc-markdown. Private helpers are excluded for brevity.

.. raw:: html

    <table border="1" style="border-collapse: collapse;">
    <thead>
        <tr><th>Module & Function</th><th>Summary</th></tr>
    </thead>
    <tbody>
        <tr><td>extractor.main(pdf_path: str)</td><td>Runs first-pass Docling + LLM extraction; returns raw JSON</td></tr>
        <tr><td>extractor.refine_extracted(raw_json, output_dir)</td><td>Applies second-pass LLM to normalize and validate output</td></tr>
        <tr><td>minio_client.download_pdf(object_name, dest)</td><td>Downloads a CSR PDF from MinIO</td></tr>
        <tr><td>minio_client.list_objects(prefix)</td><td>Lists all files in a given MinIO directory prefix</td></tr>
        <tr><td>batch.run_single(key)</td><td>Executes full extraction for a single file</td></tr>
        <tr><td>batch.run_batch(prefix, limit)</td><td>Batch-mode extractor for a report directory</td></tr>
        <tr><td>db.ingest.ingest_report(json_path, company)</td><td>Validates and ingests records into MongoDB + PostgreSQL</td></tr>
        <tr><td>postgres_operations.create_tables()</td><td>Initializes PostgreSQL schemas for indicator storage</td></tr>
        <tr><td>postgres_operations.insert_records(records)</td><td>Inserts validated records via batch insert</td></tr>
        <tr><td>viz.app.py (Flask)</td><td>Serves dashboards and data validation endpoints</td></tr>
    </tbody>
    </table>

Full HTML documentation: Run poetry run pydoc-markdown -m modules -I . -o docs/api.html and open docs/api.html in a browser.