Batch Processing
================
================


Batch Processing and Lineage Control
----------------------------------------
The batch processing component acts as the operational backbone of the entire CSR data extraction pipeline. It coordinates the systematic ingestion, extraction, validation, and storage of multiple CSR reports in a robust and reproducible manner. The batch processing system is specifically engineered to handle varying data volumes, maintain idempotency, and provide full traceability through lineage management.

Batch Execution Logic
^^^^^^^^^^^^^^^^^^^^^^^^^^^
At the core of the batch architecture lies the run_batch() function, responsible for coordinating the processing of documents stored within MinIO object storage. This function automates a sequence of steps to manage data flow efficiently from retrieval to storage.
The process begins by retrieving all relevant file keys from the MinIO bucket using the list_objects() function. If a limit parameter is specified, the function selects only the first N keys; otherwise, it processes all available files. This initial filtering ensures flexible scaling, allowing the pipeline to accommodate test runs and production-scale ingestion seamlessly.
Before any extraction is performed, the system checks whether each document has already been processed. This is achieved by querying the csr_lineage collection in MongoDB to determine if a record associated with the current object key exists. Documents that have been previously processed are automatically skipped. This lineage check plays a crucial role in enforcing idempotency, preventing duplicated entries and optimising resource usage.
For every document key that passes the lineage check, the pipeline executes run_single(key). This function encapsulates the entire processing logic for a document, including downloading from MinIO, applying page filters, executing the two-pass LLM extraction, validating the output, and inserting the final records into MongoDB. The system maintains counters for successful and failed executions, logging the outcomes at the end of each batch for transparency and diagnostic purposes.
Upon completion, a summary is printed, highlighting the number of successful extractions and identifying any failures for further inspection. This structured approach ensures the pipeline can operate autonomously and reliably, even across large datasets.

Idempotency and Reproducibility
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
A fundamental design goal of the batch processing system is to ensure idempotency—namely, that reprocessing the same input files will not result in duplicate records or inconsistent database states. This design principle is vital in environments where batch operations may be interrupted or rerun.
To support this, three mechanisms are integrated. First, the system performs a lineage check before each document is processed, avoiding reprocessing previously handled files. Second, data ingestion is performed as an atomic transaction: a document is either fully processed and its lineage metadata recorded, or not processed at all. This ensures that partial or failed extractions do not leave inconsistent states. Third, output files are stored in predictable and consistent paths, simplifying overwrite operations, audits, and file version comparisons.
This approach provides a robust safeguard against data duplication and ensures the pipeline remains dependable under both normal operations and edge cases such as system crashes or connection failures.

Future Improvements to Batch Processing
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
While the current batch infrastructure is functional and stable, several enhancements have been proposed to elevate its efficiency and adaptability. One such improvement is the adoption of asynchronous processing through Python’s asyncio library or distributed task queues like Celery. This would allow concurrent handling of multiple documents, significantly reducing batch execution time.
Another area of development involves robust error recovery. Introducing automatic retry mechanisms for transient errors—such as network instability or temporary database unavailability—would improve reliability and reduce the need for manual reruns. Additionally, dynamic load balancing could be implemented by partitioning batch tasks and distributing them across multiple containers or nodes, particularly within a Kubernetes-based deployment. This would optimise resource usage and facilitate horizontal scaling.
Finally, lineage tracking can be extended beyond internal metadata by integrating industry-standard frameworks such as OpenMetadata. This would enable richer querying, visualisation, and lineage navigation through graphical interfaces, improving transparency for both developers and end users.
Collectively, these improvements aim to ensure that the batch processing component remains resilient, scalable, and well-aligned with best practices in modern data engineering.

Chapter 3: Validation and Quality Assurance