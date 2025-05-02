Visualization Tool
==================
==================


Visualization and Analytics Tool
------------------------------------
To support downstream ESG data analysis, a web-based dashboard and visualization platform was developed using Flask and Chart.js. The system enables interactive exploration of extracted ESG metrics, helping analysts monitor historical trends, assess target progress, and perform multi-dimensional comparisons.

Dashboard Overview
^^^^^^^^^^^^^^^^^^^^^^^^
The main dashboard page allows users to:
Select a company, one or more years, and a specific ESG indicator;
View an interactive line chart (rendered with Chart.js) showing KPI trends over time;
See the corresponding data table with numeric values per year.

Figure 3: CSR Dashboard for Apple
The displayed interface is part of an interactive CSR Dashboard designed to visualize ESG metrics over time. In this example, the selected company is Apple Inc., and the chosen indicator is Scope 1 emissions (direct greenhouse gas emissions). The user has selected the years 2017 to 2021 for analysis. On the left, a line chart illustrates the emission trend across these years, showing a peak in 2018 at 57,440 tCO₂e, followed by a steady decline and a slight rebound in 2021 to 55,200 tCO₂e. On the right, a data table provides the exact emission values for each year, allowing for both visual and numerical reference. The dropdown menus at the top allow users to dynamically change the company, indicator, and time range, enabling flexible and targeted analysis.
One of the core features of the visualization system is Trend Analysis, which enables users to explore historical time series of ESG indicators across multiple years. As shown in Figure 3, the dashboard allows users to select a company (e.g., Apple Inc.), a set of years (e.g., 2017–2021), and a specific ESG metric such as Scope 1 emissions. The selected data is then rendered as an interactive line chart, allowing users to observe fluctuations and long-term patterns in the indicator values. This type of temporal visualization is critical for identifying performance anomalies, year-over-year improvements, or regressions in environmental targets. Alongside the chart, a synchronized data table provides the exact values for each selected year, offering both visual and numerical clarity.
The entire dashboard is powered by asynchronous API calls to a backend endpoint (/api/dashboard_data), which dynamically filters and retrieves relevant metrics from structured JSON files exported from the ESG extraction pipeline. This design ensures responsive interaction and a seamless user experience when working with large-scale corporate sustainability data.
By presenting KPIs in both chart and tabular formats, the system supports deeper insight into how ESG performance evolves over time and facilitates data-driven assessments for benchmarking, compliance monitoring, and strategic planning.

Multi-Dimensional Visualization
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The Data Visualization page provides an interactive environment where users can perform customized visual analysis of ESG indicators across companies, years, and metrics. As illustrated in Figure 4, this interface supports exploratory data visualization in a highly flexible manner.

Figure 4: CSR Dashboard for Apple
Functional Overview:
Search Company
At the top of the page, users can type and search for a company using fuzzy search, allowing for partial matches and flexible name input. This makes it easy to quickly locate firms even if the full name is not known.
Select Years
A scrollable multi-select list allows users to choose one or more reporting years (e.g., 2017–2024). This supports temporal analysis over short or long time horizons.
Select ESG Metrics
Another scrollable list provides a wide array of ESG indicators—such as scope1_emissions, net_zero_target_year, or water_withdrawal. Users can select one or multiple metrics to be plotted in the same chart, enabling cross-indicator comparison for a given company or across firms.
Chart Type Dropdown
A dropdown menu lets users choose the desired chart type, including Line, Bar, or Pie. This enables flexibility in visual presentation depending on the use case (e.g., trend analysis, category comparison, share breakdown).
Render Chart Button
Once selections are made, clicking the “Render Chart” button triggers the backend to fetch and process the relevant data, dynamically displaying the requested chart on the page.