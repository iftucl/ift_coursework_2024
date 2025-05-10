Architectural Motivation
========================
========================


Architectural Motivation and Rationale
------------------------------------------
To design a robust extraction system tailored for heterogeneous Corporate Social Responsibility (CSR) reports, we critically evaluate three representative approaches—DocTR, FinancialBERT, and ESG-BDL. Each embodies strengths in specific contexts yet exposes critical limitations when applied to ESG-specific workflows.
DocTR, a CNN-Transformer-based OCR engine, offers high-fidelity text localization and recognition across diverse PDF formats and resolutions (DocTR, 2021). However, its domain-agnostic architecture lacks semantic awareness, necessitating labor-intensive post-processing to distinguish between visually similar but semantically distinct elements, such as carbon disclosure tables and financial statements. This shortcoming becomes particularly evident in ESG-specific applications, where contextual interpretation is critical. To address this, we repurpose DocTR as a visual backbone in our architecture and enhance its utility by integrating domain-aware large language model (LLM) layers, which semantically filter and contextualize the OCR outputs.
FinancialBERT, a RoBERTa-based language model fine-tuned on structured financial disclosures such as SEC 10-K and 10-Q filings (Liu et al., 2019), demonstrates robust performance in entity recognition within HTML-based document structures. However, its heavy reliance on the Document Object Model (DOM) renders it ineffective for scanned CSR PDFs, where spatial relationships are visually rather than programmatically defined. When applied directly to OCR-extracted text, it struggles with unordered or fragmented input streams—such as merged columns or misaligned section headers—resulting in semantic distortion. Our system mitigates this limitation by confining linguistic analysis to OCR outputs that have undergone layout-aware reconstruction, thereby preserving document semantics and enabling meaningful interpretation.
ESG-BDL (ESG Bottom-up Data Labeller) exemplifies a rule-based, template-driven approach that uses XPath and regular expressions to extract tabular data from EU banking reports (Chen et al., 2021). While highly precise within narrowly defined templates, ESG-BDL suffers from significant performance degradation—up to 40%—when applied to documents with layout variability or multilingual headers (e.g., ‘CO₂e’ vs. ‘CO2 equivalent’). This brittleness arises from hardcoded syntactic patterns. Our architecture addresses this challenge through prompt-based LLM extraction, trained on few-shot examples of semantic equivalences (e.g., ‘Scope 3’ ≈ ‘Supply Chain Emissions’), thereby achieving adaptability without the need for manual rule reconfiguration.

.. raw:: html

    <table border="1" style="border-collapse: collapse;">
    <thead>
        <tr><th>Method</th><th>Strengths</th><th>Limitations</th><th>Improvement in Our System</th></tr>
    </thead>
    <tbody>
        <tr><td>DocTR</td><td>- Accurate OCR via CNN-Transformer architecture - Works across diverse PDF formats</td><td>- Lacks semantic understanding - Cannot differentiate ESG-specific structures</td><td>Used as a visual backbone in Pass-1; semantic filtering added via LLM in Pass-2</td></tr>
        <tr><td>FinancialBERT</td><td>- Effective in entity recognition within structured HTML (e.g., SEC 10-K/Q)  - Financially contextualized language model</td><td>- Depends on DOM; ineffective for scanned PDFs - Fails on visually arranged text structures</td><td>Avoided direct use; we apply layout-aware reconstruction before linguistic analysis</td></tr>
        <tr><td>ESG-BDL</td><td>- High precision in rule-defined templates - Effective on consistent layouts</td><td>- Fragile under layout or language variation - Requires manual rule updates</td><td>Replaced with prompt-based LLM extraction, trained via few-shot semantic examples</td></tr>
    </tbody>
    </table>

Table 5:Comparison and Integration of Existing Approaches in Our System
These limitations motivate our two-pass architecture, which synthesizes the visual generalization strength of DocTR with the contextual inference capabilities of domain-aware large language models (LLMs). In the first pass, DocTR serves as a visual backbone to maximize textual recall from scanned and native PDFs. In the second pass, a cascaded LLM framework—based on Llama-4 variants—semantically filters and aligns extracted content to a canonical schema. This decoupled design not only enhances robustness across document formats and languages but also resolves critical normalization challenges, including unit harmonization and temporal alignment. By embedding a JSON Schema validation layer and maintaining traceability via MinIO-MongoDB lineage links, the system ensures syntactic integrity and auditability throughout the extraction pipeline.

Figure 1: Two-pass Architecture