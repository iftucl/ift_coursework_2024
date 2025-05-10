Architecture Overview
=====================
=====================


Overview
------------
Our automated CSR report processing system is designed as a modular and scalable data pipeline that transforms unstructured sustainability disclosures into standardized ESG indicators. It integrates OCR, intelligent page filtering, large language models (LLMs), and schema-based validation to ensure accuracy, auditability, and high throughput.

The system ingests CSR reports from cloud-based object storage (MinIO), processes them using a two-pass extraction framework powered by LLMs, and stores validated data in a NoSQL database (MongoDB). Metadata tracking ensures full reproducibility, while API endpoints and visualization dashboards support user-driven analytics.

Table 4 below outlines the core functional components of this architecture, highlighting the technologies used and their respective roles within the end-to-end pipeline.


.. raw:: html

    <table border="1" style="border-collapse: collapse;">
    <thead>
        <tr><th>Component</th><th>Technology & Functionality</th></tr>
    </thead>
    <tbody>
        <tr><td>Object Storage</td><td>MinIO used to store raw PDF/HTML CSR reports with version-aware naming.</td></tr>
        <tr><td>Preprocessing</td><td>Docling + TableFormer for OCR and layout-aware conversion to text with page markers.</td></tr>
        <tr><td>Pass 1 Extraction</td><td>llama-4-scout-17b-16e performs high-recall extraction of raw metrics and targets.</td></tr>
        <tr><td>Pass 2 Standardization</td><td>llama-4-maverick-17b-128e maps raw data to canonical indicators and normalizes units.</td></tr>
        <tr><td>Validation</td><td>Schema-based field checking to filter out inconsistent or incomplete records.</td></tr>
        <tr><td>Data Storage</td><td>MongoDB stores structured records (csr_reports), with lineage metadata in csr_lineage.</td></tr>
        <tr><td>Batch Orchestration</td><td>Python runner (run_batch()) coordinates execution and ensures idempotency.</td></tr>
        <tr><td>Analytics & API</td><td>Django-based dashboards and REST endpoints enable filtering by company, year, and indicator.</td></tr>
    </tbody>
    </table>

Table 7: Overview of Core System Components