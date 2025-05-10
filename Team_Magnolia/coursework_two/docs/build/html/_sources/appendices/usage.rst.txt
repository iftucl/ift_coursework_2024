Usage
=====
=====

Appendix B: Usage Instructions
B.1 Running the Pipeline
The extraction pipeline supports multiple operational modes:

.. raw:: html

    <table border="1" style="border-collapse: collapse;">
    <thead>
        <tr><th>Mode</th><th>Command</th><th>Use Case</th></tr>
    </thead>
    <tbody>
        <tr><td>Single PDF</td><td>Main.py extract --minio-key “2024/Apple Inc.pdf”</td><td>Ad-hoc extraction and debugging</td></tr>
        <tr><td>Local File</td><td>Main.py extract --pdf /path/to/report.pdf</td><td>Local testing without MinIO</td></tr>
        <tr><td>Batch by Prefix</td><td>Main.py batch-extract --prefix “2024/” --limit 100</td><td>Bulk extraction (e.g., all 2024)</td></tr>
        <tr><td>Convert Output</td><td>Main.py convert</td><td>Converts JSON to CSV for BI tools</td></tr>
    </tbody>
    </table>

B.2 Scheduling (Cron-based)
The CLI supports automation via task schedulers such as cron or Airflow.
Example cron job (process reports every Sunday at 3:00 AM):
0 3 * * SUN  cd /path/to/coursework_two && poetry run python Main.py batch-extract --prefix “2024/”
B.3 Troubleshooting Checklist

.. raw:: html

    <table border="1" style="border-collapse: collapse;">
    <thead>
        <tr><th>Symptom</th><th>Likely Cause</th><th>Resolution</th></tr>
    </thead>
    <tbody>
        <tr><td>S3Error: NoSuchKey</td><td>Key typo or bucket mismatch</td><td>Verify with MinIO web UI</td></tr>
        <tr><td>Validation failure: cannot convert float</td><td>Locale-specific numeric format</td><td>Extend _clean_numeric regex handling</td></tr>
        <tr><td>LLM 400 json_validate_failed</td><td>Model input too long</td><td>Reduce input size; split long tables</td></tr>
        <tr><td>Dashboard shows “collection empty”</td><td>No successful extraction ingested</td><td>Run a verified single-file test first</td></tr>
    </tbody>
    </table>