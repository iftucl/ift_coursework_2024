Validation Framework
====================
====================


Validation Framework and Pydantic Modelling
-----------------------------------------------
Maintaining the accuracy, consistency, and integrity of extracted CSR indicator data is paramount for producing reliable analytical outcomes. To accomplish this, the system incorporates a comprehensive validation framework built upon Pydantic—a Python data validation library that provides schema enforcement through explicit type constraints and field rules. This framework ensures that all processed records are subjected to rigorous scrutiny before being committed to storage.

Motivation for Validation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Given the unstructured nature and heterogeneity of corporate sustainability reports, extracted data is vulnerable to a range of inconsistencies and errors. These may include misinterpreted date formats (e.g., “FY22” or “2023/24”), erroneous indicator mappings, non-numeric entries in fields expected to be numeric, absent metadata such as units or indicator IDs, or improper classification of targets as metrics. Left unchecked, these issues risk propagating through analytical systems, distorting insights and undermining data-driven decisions. Hence, a systematic, programmatically enforced validation stage is essential to uphold data quality standards.

Structure of the Validation Layer
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The validation layer is designed as a self-contained module within the pipeline architecture (Arora et al., 2021). Each extracted and standardized record passes through a Pydantic BaseModel that applies strict validation rules. Key fields subjected to validation include the reporting year, the indicator ID, numeric values, measurement units, and record classification (metric or target).
Table 7 provides a summary of core validation criteria:

.. raw:: html

    <table border="1" style="border-collapse: collapse;">
    <thead>
        <tr><th>Field</th><th>Validation Rule</th></tr>
    </thead>
    <tbody>
        <tr><td>indicator_year</td><td>Must be an integer between 1900 and the current year</td></tr>
        <tr><td>indicator_id</td><td>Must match regex pattern ^[a-z0-9_]+$ (lowercase slug)</td></tr>
        <tr><td>value</td><td>Must be numeric (int or float) where applicable</td></tr>
        <tr><td>record_type</td><td>Must be either “metric” or “target” (strict enum)</td></tr>
        <tr><td>unit</td><td>Optional, but if present, must be among recognized measurement units</td></tr>
        <tr><td>confidence</td><td>Must be a float between 0 and 1</td></tr>
    </tbody>
    </table>

Table 9: Pydantic Field Validation Summary
All validation rules are enforced strictly — a record failing any single rule is immediately flagged, and the corresponding error is logged in the system.

Implementation Example
^^^^^^^^^^^^^^^^^^^^^^^^^^^^
A simplified excerpt of the Pydantic model could resemble:
from pydantic import BaseModel, Field, validator
from datetime import datetime

class CSRIndicatorRecord(BaseModel):
indicator_year: int = Field(..., ge=1900, le=datetime.now().year)
indicator_id: str = Field(..., regex=r’^[a-z0-9_]+$’)
value: float
record_type: str

@validator(‘record_type’)
def validate_record_type(cls, v):
if v not in [‘metric’, ‘target’]:
raise ValueError(‘record_type must be either “metric” or “target”‘)
return v
This formal schema ensures that every record entering the database adheres to a consistently validated structure, minimizing risks of downstream corruption.