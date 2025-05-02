Workflow
========
========


Detailed Workflow of the System Architecture
------------------------------------------------
The overall system architecture for the CSR data extraction project is designed to be modular, scalable, and highly automated, ensuring that raw CSR reports can be efficiently transformed into structured and validated sustainability datasets. The architecture integrates multiple components, each responsible for distinct stages of the data pipeline, from file ingestion to final storage.
The pipeline begins with MinIO serving as the object storage layer. Companies’ CSR reports, primarily in PDF or HTML format, are stored in MinIO. Using a listing function (list_objects), the system dynamically identifies new or modified documents to be processed without manual tracking. This ensures flexibility in handling expanding datasets over time.
Once documents are identified, a batch processing engine (run_batch) coordinates the processing workflow. For each document, the engine orchestrates a series of operations including document downloading, table extraction, LLM-assisted structuring, validation, and storage. Crucially, the batch runner incorporates a lineage check — by querying the csr_lineage collection in MongoDB — to avoid redundant processing and to ensure idempotency (i.e., re-running the pipeline does not duplicate results).
The core data extraction utilizes a two-pass system powered by OCR tools (Docling + TableFormer) for text recognition and LLM models (Llama 4 variants) for intelligent table parsing and indicator standardization. This hybrid approach allows the pipeline to handle various document complexities, such as rotated tables, multi-level headers, and inconsistent formatting.
Post extraction and validation, the structured CSR data records are persisted into a dedicated MongoDB database (csr_reports collection), ensuring efficient querying and future analysis (Armbrust et al., 2021). In parallel, metadata about each execution—including document keys, runtime details, output file paths, and version tags—is recorded into the csr_lineage collection to guarantee full reproducibility and facilitate debugging.
This modular architecture ensures that each component (e.g., file ingestion, extraction, validation, storage) can be independently upgraded or extended without disrupting the entire system, providing long-term sustainability and scalability for the project (Chen et al., 2020).

Figure 2: System Architecture of the CSR Indicator Extraction Pipeline