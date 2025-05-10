Two Pass Extraction
===================
===================


Two-Pass LLM Extraction and Processing
------------------------------------------
Due to the heterogeneous structure and language used across corporate sustainability reports, a single-pass data extraction method is often inadequate to ensure both coverage and standardisation. To address this, the pipeline implements a Two-Pass LLM Extraction Strategy. This method leverages two distinct prompt-engineered large language models (LLMs), each tailored to a specific stage in the data transformation process, thereby facilitating both high recall and high precision in CSR metric extraction.

Pass 1: Raw Data Extraction
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
In the first extraction stage, the system utilises llama-4-scout-17b-16e, a lightweight yet context-aware LLM optimised for structured document interpretation. The aim of this phase is to identify all potentially relevant metrics, targets, and numerical statements from CSR pages that have already undergone filtering (Beltagy et al., 2020). The prompt logic applied to the model is intentionally broad and permissive, instructing it to locate any quantitative or goal-related statement, extract associated units and time references, and format the result according to an internally defined schema (referred to as schema-A). This schema captures fields such as metric_name, value, unit, year, and raw_snippet.
The primary design goal of Pass 1 is to maximise recall. By tolerating redundancy and accepting loosely defined structures, the model ensures that potentially useful data is not prematurely discarded. While this does introduce a degree of noise, it allows the second pass to apply stricter controls downstream. The output from this stage is saved as an intermediate JSON file (e.g., extracted_data.json), forming the input for the standardisation process in Pass 2.

Pass 2: Standardisation and Normalisation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
In the second pass, a more advanced model, llama-4-maverick-17b-128e, is employed. This model is configured for precision-focused tasks such as entity mapping and unit harmonisation. Its prompt logic builds upon the initial extracted data and performs several critical functions. First, it maps each identified metric to a corresponding entry in a pre-defined master list of indicators—such as matching “Scope 1 GHG Emissions” to the slug ghg_scope_1. Second, it normalises numerical units to canonical formats based on context (for instance, converting “million tonnes” to “tonnes”). Third, it attempts to infer missing values like baseline year or reporting type, using contextual clues from the surrounding text. Lastly, it flags records where the model’s confidence falls below a predefined threshold, indicating the need for human review or downstream caution.
This phase enforces a stricter schema (schema-B), where all core fields—including indicator_id, value, unit, year, and record_type—must either be explicitly provided or clearly marked as null. The output from this step is saved in final_standardized.json, which is then passed into the validation and persistence layers of the pipeline.

Guardrails and Output Format Control
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
To ensure robustness and output consistency, a guardrail mechanism is implemented across both LLM passes. The models are required to produce outputs strictly in JSON object format, as specified by the response_format={“type”:”json_object”} parameter. Following generation, a secondary parsing function is applied to re-validate and sanitise the output. This parser is equipped to strip markdown-style code block delimiters (e.g., “```json”) and automatically reattempt JSON parsing, thereby mitigating common formatting inconsistencies resulting from minor model hallucinations or tokenisation errors.
This two-tiered validation significantly improves system stability and reduces the likelihood of malformed outputs propagating through the pipeline.

Rationale for the Two-Pass Strategy
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Splitting the extraction process into two distinct stages yields several strategic benefits. Firstly, it allows for the separation of concerns: the first pass is optimised for breadth, ensuring no relevant data is missed, while the second pass ensures depth, refining and aligning the extracted content to standard formats. Secondly, this modular design enables independent improvements to each component. For example, updating prompt logic or replacing the underlying model for one pass can be done without impacting the other. Thirdly, retaining intermediate outputs, such as extracted_data.json, facilitates detailed debugging and error tracing, which is particularly valuable during development and quality assurance.
Furthermore, the two-pass design provides a natural insertion point for future enhancements. Additional processing stages, such as anomaly detection, document classification, or external data enrichment, could be integrated between Pass 1 and Pass 2 with minimal architectural disruption.

Limitations and Future Improvements
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Despite its effectiveness, the two-pass approach is not without limitations. One notable drawback is the risk of error propagation. Misclassifications or omissions made during the first pass may not be rectifiable in the second pass, potentially leading to inaccuracies in the final output. Moreover, this dual-stage process increases the overall computational load, as each document must undergo two separate LLM inferences, which can be resource-intensive in high-throughput scenarios.
Another key dependency is the quality of prompt engineering. Minor changes in wording or formatting of the prompts can significantly affect model performance, highlighting the importance of rigorous prompt testing and version control.
Looking ahead, future development will explore the fine-tuning of smaller, domain-specific LLMs on a curated corpus of CSR documents. By adapting models to the specific linguistic and structural patterns commonly found in sustainability reporting, the pipeline can further reduce inference time, enhance accuracy, and minimise reliance on large-scale, general-purpose APIs.