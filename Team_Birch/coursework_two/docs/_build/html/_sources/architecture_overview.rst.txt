Architecture Overview
=====================

Data Flow
---------

.. graphviz::

   digraph process_flow {
       rankdir=LR;
       node [shape=box, style="rounded,filled", fillcolor="lightgrey", fontname="Helvetica"];
       edge [arrowhead=vee];

       config [label=<
           <b>Configuration Management</b><br/>
           <i>(indicator_config.py)</i><br/>
           Load indicator definitions
       >];

       streaming [label=<
           <b>Data Streaming</b><br/>
           <i>(minio_streaming_extractor.py)</i><br/>
           Stream PDFs from MinIO
       >];

       api [label=<
           <b>DeepSeek API</b><br/>
           AI‐powered text extraction
       >];

       parsing [label=<
           <b>Content Parsing</b><br/>
           <i>(emissions_parser.py)</i><br/>
           1. Chunk PDF pages<br/>
           2. Extract text<br/>
           3. Query DeepSeek API
       >];

       logging [label=<
           <b>Logging</b><br/>
           Extraction details and validation
       >];

       post [label=<
           <b>Post-Processing</b><br/>
           <i>(postprocess.py)</i><br/>
           Normalize and validate values
       >];

       output [label=<
           <b>Output CSV</b><br/>
           Structured indicator data
       >];

       config -> streaming;
       streaming -> parsing;
       api      -> parsing;
       parsing  -> logging;
       parsing  -> post;
       post     -> output;
   }

Components
----------

- src/modules/input/: Core extraction logic ((`emissions_parser.py`), (`minio_streaming_extractor.py`), (`indicator_config.py`), (`postprocess.py`)).
- src/modules/db/data_storage.py: Stores cleaned data into PostgreSQL ((`csr_reporting.company_indicators`)).
- src/modules/output/data_clean.py: Cleans and reshapes raw extracted CSV into standardized format.
- src/modules/output/data_export.py: Merges company metadata with report information for downstream use.
- config/indicators.yaml: Indicator definitions, aliases, and validation rules.
- logs/: Stores extraction output ((`final_output.csv`)) and processing logs.
- PostgreSQL: Schema (`csr_reporting`), (`table company_indicators`), (`alongside company_reports`) and (`company_static`) for metadata.