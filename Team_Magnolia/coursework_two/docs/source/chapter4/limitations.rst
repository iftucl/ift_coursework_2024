Limitations
===========
===========


Limitations & Discussion
----------------------------
While the proposed pipeline demonstrates high performance and accuracy in extracting ESG data from corporate sustainability reports, several limitations remain that inform future system improvements:

Inline Calculations and Formula Parsing
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
In certain cases, the LLM accepted mathematical expressions directly from the PDF — such as: 1770000 / 1832000 * 100. These were occasionally misinterpreted as valid metric values during post-processing. To mitigate this, a post-regex sanitization layer was added to remove embedded expressions before unit standardization and validation. However, more robust formula detection and symbolic reasoning capabilities may be needed to fully filter out such edge cases.

Layout Challenges: Rotated Headers
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
A small subset (< 2%) of CSR documents feature rotated table headers or heavily stylized tables, which remain problematic for standard OCR and layout-parsing modules. These misalignments often cause header-value mismatches, leading to partial or missed extractions. To address this, future versions of the system will integrate RangerViT, a visual transformer architecture capable of handling diverse layout configurations with fine-grained visual-textual alignment. This will enhance robustness against non-standard formats.

Duplicate Documents and Redundant Processing
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Some companies release the same PDF under multiple names or file keys. Although the system logs processing metadata via the csr_lineage collection, duplicate PDFs are currently reprocessed unnecessarily, consuming redundant compute resources.To resolve this, To solve this problem, PDF bytes for hashing may save up to 14% of the calculation time.