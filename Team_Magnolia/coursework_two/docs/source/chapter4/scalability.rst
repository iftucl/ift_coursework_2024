Scalability
===========
===========


Scalability and Flexibility
-------------------------------
A major design goal of the pipeline was to ensure that it remains scalable and adaptable to future needs. This is achieved through several architectural choices:
Scalability across Dimensions:

.. raw:: html

    <table border="1" style="border-collapse: collapse;">
    <thead>
        <tr><th>Scalability Dimension</th><th>Description</th></tr>
    </thead>
    <tbody>
        <tr><td>More Firms</td><td>The system can ingest additional CSR PDFs from new sources simply by adding them to the MinIO bucket.</td></tr>
        <tr><td>More Indicators</td><td>New ESG indicators can be added to the master schema with minimal re-engineering, as the LLM prompt is schema-driven.</td></tr>
        <tr><td>New Standards</td><td>As ESG taxonomies evolve (e.g., EU CSRD, IFRS S1/S2), the pipeline can be adapted by updating the validation rules and schema mappings.</td></tr>
    </tbody>
    </table>

Table 15:Scalability Dimensions of the Extraction System
Flexible Schema Management:

.. raw:: html

    <table border="1" style="border-collapse: collapse;">
    <thead>
        <tr><th>Feature</th><th>Description</th></tr>
    </thead>
    <tbody>
        <tr><td>Pydantic-based Validation</td><td>Uses Pydantic configuration for record validation and schema enforcement, enabling modular updates and strong type safety.</td></tr>
        <tr><td>Multilingual and Multi-layout Support</td><td>Supports diverse document formats and languages via layout-aware OCR and prompt-tuned LLMs.</td></tr>
    </tbody>
    </table>

Table 16:Features Enabling Flexible Schema Management
Vector-Based Expansion:

.. raw:: html

    <table border="1" style="border-collapse: collapse;">
    <thead>
        <tr><th>Feature</th><th>Description</th></tr>
    </thead>
    <tbody>
        <tr><td>Semantic Vector Search</td><td>Future releases will integrate a vector database to enable fuzzy search and semantic expansion of indicators.</td></tr>
        <tr><td>User-Driven Discovery</td><td>Supports discovery of new ESG metrics beyond predefined templates, empowering flexible and adaptive analysis.</td></tr>
    </tbody>
    </table>

Table 17:Vector-Based Expansion Capability
These design features position the pipeline as a future-proof ESG data infrastructure layer, capable of supporting both current compliance demands and emerging sustainability analytics.