Architecture Overview
=====================

.. figure:: images/architecture.png
   :alt: Data Flow Diagram
   :align: center
   :width: 80%

**Figure 1.** The Data Flow and Components

   Description of Components:

   Source Layer

     Input Data: Annual Corporate Social Responsibility (CSR) Reports in PDF format
     Storage Location: MinIO bucket named report1

   Text Conversion Layer
     Script: extract_text.py
     Function:
         Uses PyMuPDF (fitz) to convert PDF to plain text
         Outputs .txt files for each report
     Output Storage: MinIO bucket named report
     Features: Logging for success/failure, skip logic for already converted files

   Indicator Extraction Layer
     Script: content_extract.py
     Function:
         Splits text into sentences using NLTK
         Applies regular expressions to extract sustainability indicators
         Selects the maximum value for each indicator when multiple matches are found
         Extracts metadata (e.g., company ID, reporting year) and computes MD5 hash
     Output Format: Structured JSON with:
         Environmental indicators (e.g., Scope 1/2/3 emissions, water withdrawal)
         Metadata (e.g., company_id, reporting_year)
         Validation support fields (__content_hash__, source path)
 
   Storage Layer
     Databases Used: PostgreSQL and MinIO
     PostgreSQL Tables:
         pdf_records: Stores metadata of reports (e.g., file name, company, year, hash)
         csr_indicators: Stores structured JSONB data for indicators
     Storage Features:
         Conflict resolution via ON CONFLICT UPSERT
         Traceability via content hash and MinIO path
         Schema-less flexibility with JSONB for evolving indicators

   Visualization Layer
     Frontend Framework: React + Tailwind CSS + Recharts
     Functionality:
         Searchable dashboard for company-level CSR metrics
         Dynamic charts and tables for 13 key indicators
         Responsive and interactive UI for multi-year comparisons