Fallback Heuristics
===================
===================


Fallback Heuristics for Data Extraction
-------------------------------------------
Despite the advanced techniques employed in page filtering and two-pass LLM extraction, there are unavoidable situations where the raw CSR reports provide incomplete, ambiguous, or inconsistently formatted information. To mitigate data loss and maintain extraction robustness, the pipeline integrates a set of fallback heuristics - systematic prioritization rules applied when primary extraction attempts are inconclusive.
Fallback heuristics act as intelligent default behaviors that ensure the maximum retention of usable information while transparently documenting areas of uncertainty for downstream users.

Year Extraction Fallback Strategy
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
In sustainability reporting, it is common for tables or metric listings to omit explicit year labels, especially when assuming a ‘current year’ context or when using baseline or target references implicitly.
The pipeline addresses missing or unclear indicator_year values through a prioritized fallback sequence:

.. raw:: html

    <table border="1" style="border-collapse: collapse;">
    <thead>
        <tr><th>Priority</th><th>Strategy</th><th>Description</th></tr>
    </thead>
    <tbody>
        <tr><td>1</td><td>Table Header Analysis</td><td>Whenever a year value is explicitly presented within the table header (e.g., ‘2022 Scope 1 Emissions’), this is used directly.</td></tr>
        <tr><td>2</td><td>Baseline Year Detection</td><td>If a baseline year (e.g., “Baseline (2019)”) is found near the metric and no reporting year is present, it assigns the baseline year as the reporting year.</td></tr>
        <tr><td>3</td><td>Target Year Detection</td><td>If only a target year is mentioned (e.g., “Reduce emissions by 2030”) and no current/baseline year is stated, the target year is used temporarily, with a flag.</td></tr>
        <tr><td>4</td><td>Filename Year Inference</td><td>If no internal year is available, infers the year from the document filename (e.g., “Company_CSR_2022.pdf” → 2022).</td></tr>
        <tr><td>5</td><td>Missing Year (Manual Review)</td><td>If all else fails, the record is marked as incomplete, and queued for manual review.</td></tr>
    </tbody>
    </table>

Table 10: Year Extraction Fallback Strategy
This multi-level fallback ensures that a plausible year is attached to the majority of extracted indicators, reducing data sparsity without introducing undue inaccuracies.

Indicator Name Fallback Strategy
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Another common challenge arises when the indicator name is missing, abbreviated, or expressed in an unconventional manner. The fallback heuristic for indicator name extraction follows this logic:

.. raw:: html

    <table border="1" style="border-collapse: collapse;">
    <thead>
        <tr><th>Priority</th><th>Strategy</th><th>Description</th></tr>
    </thead>
    <tbody>
        <tr><td>1</td><td>Explicit Header or Label</td><td>Direct mapping is used when clear indicator headers like “Total Water Withdrawal” are present.</td></tr>
        <tr><td>2</td><td>Slugify Available Labels</td><td>When names are malformed or abbreviated (e.g., “Scope1”), slugification is applied: a) Lowercasing text b) Replacing spaces with underscores c) Removing non-alphanumeric characters d) Fuzzy matching to known indicators</td></tr>
        <tr><td>3</td><td>Manual Mapping Flagging</td><td>If confidence in automated mapping is low, the record is flagged for manual review to preserve accuracy and auditability.</td></tr>
    </tbody>
    </table>

Table 11: Indicator Name Fallback Strategy
This approach maximizes the number of mappable indicators while preserving an audit trail of uncertain mappings.

Value and Unit Normalization Fallback
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Occasionally, extracted numeric values may be accompanied by ambiguous or missing unit descriptors. The fallback heuristics for units and values include:
Contextual Inference: when possible, adjacent text such as column headers (e.g., “Tonnes of CO2e”) is used to infer the intended units for the values.
Assumed Standard Units: for critical indicators (e.g., GHG emissions, energy consumption), if no units are stated but typical units are known from reporting standards, the standard unit is assumed and annotated accordingly.
Flagging for Review: if neither inference nor assumption yields a confident result, the record is extracted with a “unit_missing” flag to allow focused manual curation.

Principles Behind Fallback Heuristics
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The design of fallback heuristics follows several key principles:
Conservatism: default assumptions are made only when supported by strong contextual evidence to avoid introducing errors (Ratner et al., 2020).
Transparency: all fallback applications are logged and flagged, allowing analysts to distinguish between confidently extracted data and data recovered through heuristic methods.
Traceability: each fallback action is recorded in the record metadata (e.g., “year_inferred_from_filename”,”indicator_slugified_from_label”), aintaining a full audit trail.
Prioritization of Completeness over Perfection: in large-scale datasets, it is often preferable to capture imperfect but improvable data rather than systematically discard uncertain entries.