Page Filtering
==============
==============


Page Filtering Strategy
---------------------------
Before initiating intensive table extraction and LLM-based processing, it is essential to efficiently identify and prioritize the most relevant pages from the raw CSR reports. Given that CSR reports often span hundreds of pages, and relevant sustainability indicators are typically concentrated in only a few sections, an intelligent page filtering mechanism dramatically improves both processing efficiency and data quality (Gao et al., 2022).
To address this need, the pipeline implements a regex-driven page filtering strategy. The goal of this stage is twofold: firstly, to pre-select pages highly likely to contain key metrics or targets; and secondly, to minimize unnecessary LLM queries, thereby reducing computational costs and error propagation.
The filtering process applies three core heuristic checks on each page’s extracted text:
Unit Detection (unit_re):
A regular expression is employed to detect the presence of standard measurement units commonly associated with CSR metrics, such as tCO₂e (tonnes of CO₂ equivalent), MWh (megawatt-hours), or ML (megalitres). Pages lacking any recognised units are deprioritized, under the assumption that they are less likely to contain quantitative indicator data.
Keyword Density Threshold (≥ k keyword hits):
Each page is scanned for the presence of a predefined set of thematic keywords, including but not limited to “Scope 1”, “Scope 2”, “Renewable Electricity”, “Energy Consumption”, and “Water Usage”. Only pages achieving a minimum number of keyword matches (k) are retained for further processing. This ensures that narrative-only sections, such as forewords or corporate strategy discussions, do not overwhelm the extraction models.
Calendar Year Mentions (≥ 2 year mentions):
Pages are also assessed for the frequency of calendar year references (e.g., “2022”, “2023”). Sustainability reporting sections often include tables with multiple years of data, while non-quantitative sections typically mention fewer dates. A threshold of at least two distinct year mentions is imposed to further enhance filtering precision.
Only pages that pass all three filtering criteria are selected for the extraction pipeline. Pages that partially meet the conditions may still be included in borderline cases, but with a lower processing priority.
To validate the effectiveness of the page filtering strategy, a hand-labelled validation set comprising 500 manually reviewed pages was created. Testing on this set yielded the following results:

.. raw:: html

    <table border="1" style="border-collapse: collapse;">
    <thead>
        <tr><th>Metric</th><th>Value</th><th>Description</th></tr>
    </thead>
    <tbody>
        <tr><td>Recall</td><td>92%</td><td>92% of truly relevant pages were successfully captured by the filtering rules</td></tr>
        <tr><td>Precision</td><td>84%</td><td>84% of pages selected by the rules were indeed relevant to sustainability indicators</td></tr>
    </tbody>
    </table>

Table 8: Page Filtering Evaluation Metrics
These figures confirm that the page filtering mechanism achieves a high level of effectiveness, balancing comprehensive coverage of relevant data against the minimization of unnecessary processing overhead.
Moreover, by reducing the input size for downstream LLM passes, the system achieves not only speed gains but also improves extraction accuracy, as irrelevant or noisy content is less likely to mislead the models.
In future iterations, the page filtering strategy can be further refined by incorporating machine learning-based page classification models trained on labelled CSR datasets, allowing even finer discrimination between relevant and non-relevant content.