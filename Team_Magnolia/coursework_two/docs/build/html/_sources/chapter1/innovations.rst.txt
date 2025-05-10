Innovations
===========
===========


Key Features and Innovations of the Project
-----------------------------------------------

Modular Two-Pass Extraction Architecture
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
At the heart of the framework lies a two-stage large language model (LLM) extraction pipeline optimized for both recall and precision:
Pass 1: High-Recall Extraction: Utilizes a lightweight LLM (scout-17b-16e) to broadly identify candidate ESG metrics, numeric values, units, and contextual language. It favors coverage, capturing all potentially relevant content—even if noisy or incomplete.
Pass 2: Precision-Oriented Refinement: Applies a more powerful LLM (maverick-17b-128e) to normalize, validate, and map extracted candidates to canonical indicators defined in the ESG data dictionary. This phase includes unit standardization, year inference, and record deduplication.
This two-pass design resolves the inherent tension between over-extraction and under-specification, enabling consistent structured output across diverse reporting styles and layouts.

Schema-Driven Validation and Consistency Enforcement
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Each extracted record is validated against a rigorously defined JSON schema:
indicator_id must match pre-approved slugs
unit must belong to a thematic whitelist (e.g., tCO₂e for environmental metrics)
values_numeric arrays must align with years
Any failure results in either quarantining or rejection of the record
This approach ensures all data ingested into MongoDB (csr_reports) is internally consistent, externally interpretable, and semantically aligned with the data catalogue.

Scalability and Automation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Built as a linear batch-processing engine with Dockerized deployment, the system supports:
Automated ingestion of 1,000+ CSR reports per day
Scheduled batch jobs for periodic updates (via cron or Airflow)
Selective reprocessing based on lineage metadata and model version changes
This allows the pipeline to scale horizontally while maintaining fault isolation and output stability.

Technical Design Highlights
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. raw:: html

    <table border="1" style="border-collapse: collapse;">
    <thead>
        <tr><th>Feature</th><th>Purpose</th></tr>
    </thead>
    <tbody>
        <tr><td>Unit Normalization</td><td>Converts colloquial units into canonical formats (e.g., “tonnes” → tCO₂e)</td></tr>
        <tr><td>Temporal Validation</td><td>Ensures logical order (e.g., target_year > report_year)</td></tr>
        <tr><td>Error Isolation</td><td>Quarantines invalid records to avoid polluting analytics datasets</td></tr>
        <tr><td>Versioning & Reproducibility</td><td>Ensures consistent outputs through version_tag and lineage records</td></tr>
    </tbody>
    </table>

Table 6: Technical Mechanisms for Ensuring Data Quality and System Reliability

Strategic Implications
^^^^^^^^^^^^^^^^^^^^^^^^^^^^
By anchoring every component—from extraction to validation to storage—in a traceable and rule-driven framework, the system provides:
Trustworthy ESG data for analysts, regulators, and investors
Repeatable results under evolving extraction logic
Infrastructure resilience across reporting formats and volumes
This positions the framework not only as a technical tool, but as a scalable backbone for data-driven sustainability governance.

Chapter 2 Architecture and Infrastructure Design