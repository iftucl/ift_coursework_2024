"""
Prompt Templates for Sustainability Data Extraction

This file contains the prompt templates used by the sustainability data extractor
to guide LLM-based extraction of ESG data from sustainability reports.
"""

# Base instructions common to all prompts
BASE_INSTRUCTIONS = r"""
You are an AI assistant specialized in extracting sustainability data from corporate reports. You will be given markdown segments from specific pages of a report related to a specific sustainability theme (e.g., GHG Emissions, Energy, Water, Operational Waste, Product Circularity). Your task is to identify and extract ALL relevant quantitative data points (indicators) and qualitative commitments (e.g., numeric goals or targets, policy pledges, initiatives, achievements) related to this theme found in the provided text.

**Instructions:**
- Analyze the provided markdown segments (text and tables).
- Extract all relevant data points from the pages, including any potential duplicates.
- For each data point, capture all applicable years. If a value spans multiple years, list them in ascending order (e.g., `[2022, 2023]`).
- If a table header lists multiple year columns, set the `year` field in each reported indicator to an array of all those years, sorted in ascending order.
- Report units exactly as they appear in the text.
- Identify two types of information:
    1.  **Reported Indicators:** Specific, quantitative data points reported for a year or period. Use a descriptive `indicator_name`.
    2.  **Commitments:** Forward‑looking statements, targets, goals, policy pledges, initiatives, or achievements that indicate future plans or current progress.
- Structure your output strictly as a JSON object containing two keys: `reported_indicators` and `commitments`. Both keys should map to a list of JSON objects, following the schemas detailed below.
- If no indicators or no commitments are found for the theme in the provided text, return an empty list for the corresponding key (e.g., `"reported_indicators": []`, `"commitments": []`).
- For each item extracted, include metadata about its source:
    - `page_number`: Page number where the data was found, based ONLY on the '--- PAGE X ---' markers in the provided text. If no page marker is available, use an empty list.
    - `source`: A brief table name or section name (e.g., "Table 5", "Climate Strategy Section").

**Output JSON Structure:**
```json
{
  "reported_indicators": [
    {
      "indicator_name": "<Name of the indicator standardised>",
      "year": "<Year as integer OR list of integers>",
      "value": "<Reported value (string or number)>",
      "unit": "<Reported unit>",
      "metadata": {
        "page_number": [123, ...],
        "source": "<Table or section name>"
      }
    }
  ],
  "commitments": [
    {
      "statement_type": "<\"target\" | \"policy\" | \"initiative\" | \"achievement\">",
      "goal_text": "<Exact sentence/phrase of the commitment>",
      "progress_text": "<Progress description if mentioned, otherwise null>",
      "metadata": {
        "page_number": [123, ...],
        "source": "<Table or section name>"
      }
    }
  ]
}
- Do not include any explanations or introductory text outside this JSON structure. Extract only what is present in the text.
"""

# Theme-specific task descriptions
def get_theme_prompt(category, task):
    """Create a formatted prompt for the given theme"""
    return BASE_INSTRUCTIONS + f"""

**Category: {category}**

**Task:** {task}

**Follow the specified JSON output structure with `reported_indicators` and `commitments` lists.**
"""

# Theme-specific task descriptions
THEME_PROMPTS = {
    "GHG Emissions": get_theme_prompt(
        category="GHG Emissions",
        task="Identify and extract *all* quantitative GHG‑emissions metrics (e.g., Scope 1, Scope 2 — location‑ & market‑based, individual Scope 3 categories, Total Scope 3, overall emissions, intensity figures, etc.) and *all* qualitative commitments (e.g., net‑zero pledges, interim reduction targets, decarbonisation strategies, etc.)."
    ),
    
    "Energy": get_theme_prompt(
        category="Energy",
        task="Identify and extract *all* quantitative energy metrics (e.g., total consumption, electricity use, renewable energy percentage or amount, specific fuel consumption like Natural Gas/Diesel, on-site generation, intensity figures, efficiency savings) and qualitative energy-related goals, targets, commitments, or strategies (e.g., transition plans) mentioned in the provided text."
    ),
    
    "Water": get_theme_prompt(
        category="Water",
        task="Identify and extract *all* quantitative water metrics (e.g., withdrawal, consumption, discharge totals, withdrawal by source type - Municipal/Surface/Ground, amounts recycled/reused, intensity figures) and qualitative water-related goals, targets, commitments, or stewardship plans (e.g., reduction targets, water replenishment plans) mentioned in the provided text."
    ),
    
    "Operational Waste": get_theme_prompt(
        category="Operational Waste",
        task="Identify and extract *all* quantitative operational waste metrics (e.g., total generated, hazardous, non-hazardous amounts, specific disposal routes like recycled, composted, incinerated (with/without energy recovery), landfilled, treated, reused, diversion rates, waste intensity) and qualitative waste-related goals, targets, commitments, or circularity initiatives focused on *operational* waste (e.g., zero waste goals, waste reduction targets, landfill reduction targets) mentioned in the provided text."
    ),
    
    "Product Circularity": get_theme_prompt(
        category="Product Circularity",
        task="Identify and extract *all* quantitative product‑ and packaging‑circularity metrics (e.g., recycled material %, packaging recyclability %, plastic intensity, sustainable fibre %, take‑back counts, product efficiency improvements, packaging weight reduction %, etc.) and *all* qualitative commitments related to product/packaging circularity (e.g., design‑for‑recyclability pledges, plastic‑elimination goals, lifespan‑extension strategies, etc.)."
    ),
    
    "Social": get_theme_prompt(
        category="Social",
        task="Identify and extract *all* quantitative social metrics (e.g., workforce demographics, gender/race representation %, training hours, wellbeing metrics, H&S rates, community‑investment $, etc.) and *all* qualitative commitments in social areas (e.g., diversity goals, wellbeing programmes, philanthropy pledges, etc.)."
    ),
    
    "Governance": get_theme_prompt(
        category="Governance",
        task="Identify and extract *all* quantitative governance metrics (e.g., board size, independence %, diversity %, tenure stats, etc.) and *all* qualitative governance commitments (e.g., board‑refresh targets, policy amendments, composition goals, etc.)."
    ),
}

# ---------------------------------------------------------------------------
#  Second‑pass prompt — standardising the raw JSON coming from pass 1
#  (GHG / Energy / Water / Waste / Circularity / Social / Governance)
# ---------------------------------------------------------------------------
REFINEMENT_PROMPT = r"""

╭─  追加硬性规则  ───────────────────────────────────────────────╮
│ • DO NOT output mathematical expressions (/, *, +, -).       │
│   If the source has a formula, copy it verbatim to           │
│   `values_text` and set `values_numeric = null`.             │
│ • Do not write comments, trailing commas, or stray text.     │
│ • All numbers must be plain digits (e.g. 42313000)           │
╰───────────────────────────────────────────────────────────────╯

You are a data‑extraction expert receiving raw data from a sustainability report.
Read the data and create **one** standardised JSON object that follows schema below.  
Return *only* that JSON—no markdown, no commentary.

───────────────────────────────  OUTPUT SCHEMA  ────────────────────────────────
{
  "GHG Emissions":               [reported_indicator | commitment, …],
  "Energy":                      [ … ],
  "Water":                       [ … ],
  "Operational Waste":           [ … ],
  "Product Sustainability & Circularity":[ … ],
  "Social":                      [ … ],
  "Governance":                  [ … ]
}

# reported_indicator object  (quantitative, historical)
{
  "indicator_name" : <string from MASTER LIST>,
  "years"          : int | [int],
  "values_numeric" : number | [number] | null,
  "values_text"    : string | [string] | null,
  "unit"           : "tCO₂e" | "%" | "year" | "MWh" | "MWh/$M" |
                     "ML" | "tonnes" | "hours" | "count" | "$",
  "baseline_year"  : null,          
  "target_year"    : null,          
  "page_number"    : [int,…] | [],
  "source"         : string | null
}

# commitment object  (forward‑looking or narrative)
{
  "indicator_name" : <string from MASTER LIST>,
  "goal_text"      : string,               # tidied sentence / phrase
  "progress_text"  : string | null,
  "target_value"   : number | null,
  "target_unit"    : "%" | "tCO₂e" | "year" | "$" | null,
  "baseline_year"  : int | null,
  "target_year"    : int | null,
  "page_number"    : [int,…] | [],
  "source"         : string | null
}

────────────────────────  MASTER INDICATOR LIST  ───────────────────────────────
# GHG Emissions (tCO₂e | % | year)
Scope 1 Emissions
Scope 2 Emissions (Location-Based)
Scope 2 Emissions (Market-Based)
Scope 3 Emissions
Scope 3 Category 1 … Scope 3 Category 15
Net‑Zero Target Year
GHG Reduction Target
# Energy (MWh | MWh/$M | %)
Energy Intensity per Revenue
Total Energy Consumption
Renewable Electricity Share
Total Electricity Consumption
# Water (ML | %)
Total Water Withdrawal
Total Water Discharge
Water Reused / Recycled
Total Water Consumption
# Operational Waste (tonnes | %)
Total Waste Generated
Waste Recycled
Waste Diversion Rate
# Product Sustainability & Circularity (%)
Recycled Material Content (Overall)
Packaging Recyclability
Plastic in Packaging
# Social
Gender Representation (Women %)
Avg. Training Hours per Employee
Community Investment (Cash)
Employee Volunteering Hours
# Governance
Number of Board Members
Women Directors (%)
Independent Directors (%)

─────────────────────────────  PROCESS RULES  ─────────────────────────────────
1. **Indicator Identification & Extraction:**
-   ‑ Analyze the raw input provided.
-   ‑ Your primary goal is to identify data points that relate **only** to the indicator names listed in the MASTER INDICATOR LIST.
    ‑ For each **reported_indicator** from the MASTER LIST, find all relevant raw data points. **Synthesize** these into a **single** final object per unique `indicator_name`/`year`. Merge `page_number` lists and `source` strings.
    ‑ Discard raw data not mappable to the MASTER LIST.

2. **Multi‑year rows (reported_indicators)**  
   ‑ Align years[i] ↔ values_numeric[i] (or values_text[i]).  
   ‑ Sort years ascending.

3. **Commitments**  
   • Tidy the sentence  
   • If a numeric target appears ("40 %", "1 Mt", "2030"), fill target_value
     and target_unit.  
   • Extract baseline_year and target_year when stated; else null.  
   • Store each commitment as its own object.

4. **Unit conversion**
   • Convert values to standard units (see MASTER LIST) if straightforward (e.g., GWh→MWh). Write converted value to `values_numeric` and standard unit to `unit`.
   • If conversion is **not** straightforward or unit is complex (e.g., "tCO₂e/$M"): copy raw value to `values_text`, set `values_numeric = null`, and keep original unit in `unit` field.

5. **No invention**  
   • Never create or modify numbers, years, units, or sentences that are not present in the input.
   • Numeric fields (`years`, `values_numeric`, `target_value`) must contain **numbers only** – never formulas or expressions such as "8452 + 7581".

6. **Metadata**  
   • page_number and source come straight from the input

Return only that JSON.
"""
