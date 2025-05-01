"""
Load and visualize ESG data from PostgreSQL database.
"""

import sys
import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import io
import base64

current_dir = os.path.dirname(os.path.abspath(__file__))        
project_root = os.path.abspath(os.path.join(current_dir, ".."))
sys.path.insert(0, project_root)

from db_utils.postgres import PostgreSQLDB
from data_models.metrics import IndicatorUnits, IndicatorNames, IndicatorCategory


def load_all_esg_data():
    """
    Load all ESG metric data from PostgreSQL database and return as a DataFrame.
    """
    with PostgreSQLDB() as db:
        # Fetch data from PostgreSQL tables
        emissions = pd.DataFrame(db.fetch("SELECT * FROM csr_metrics.emissions;"))
        energy = pd.DataFrame(db.fetch("SELECT * FROM csr_metrics.energy;"))
        waste = pd.DataFrame(db.fetch("SELECT * FROM csr_metrics.waste;"))

        emissions["table"] = "emissions"
        energy["table"] = "energy"
        waste["table"] = "waste"

        df_all = pd.concat([emissions, energy, waste], ignore_index=True)

        df_all = df_all.rename(columns={
            "company": "company_name",
            "year": "year",
            "figure": "value",
        })

    return df_all


def plot_company_all_three_categories(df_all, company_name):
    """
    Plot all three categories of ESG metrics for a given company. Return a base64 encoded image.
    """
    fig, axs = plt.subplots(3, 1, figsize=(10, 15))
    for ax, (category, indicator_ids) in zip(axs, IndicatorCategory.MAP.items()):
        df_cat = df_all[(df_all["company_name"] == company_name) & (df_all["indicator_id"].isin(indicator_ids))]

        for ind_id in indicator_ids:
            sub_df = df_cat[df_cat["indicator_id"] == ind_id]
            if not sub_df.empty:
                try:
                    label = IndicatorNames[ind_id].value
                except KeyError:
                    label = ind_id
                sns.lineplot(x="year", y="value", data=sub_df, label=label, marker="o", ax=ax)

        ax.set_title(f"{company_name} - {category}")
        ax.set_xlabel("Year")
        ax.xaxis.set_major_locator(plt.MaxNLocator(integer=True))
        ax.grid(True)

    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    buf.close()
    plt.close()
    return img_base64


def compare_companies_metrics(df_all, company_names, indicators):
    """
    Compare ESG metrics for multiple companies and return a base64 encoded image.
    """
    # Build id_to_name and name_to_id from IndicatorNames
    id_to_name = {ind.name: ind.value for ind in IndicatorNames}
    name_to_id = {v: k for k, v in id_to_name.items()}

    indicator_ids = []
    for i in indicators:
        if i in id_to_name:
            indicator_ids.append(i)
        elif i in name_to_id:
            indicator_ids.append(name_to_id[i])
        else:
            print(f"Unknown indicator: {i}")

    fig, axs = plt.subplots(len(indicator_ids), 1, figsize=(10, 5 * len(indicator_ids)))
    if len(indicator_ids) == 1:
        axs = [axs]

    for ax, ind_id in zip(axs, indicator_ids):
        ind_name = IndicatorNames[ind_id].value if ind_id in IndicatorNames.__members__ else ind_id
        df_plot = df_all[(df_all["company_name"].isin(company_names)) & (df_all["indicator_id"] == ind_id)]

        for company in company_names:
            df_c = df_plot[df_plot["company_name"] == company]
            if not df_c.empty:
                sns.lineplot(x="year", y="value", data=df_c, marker="o", label=company, ax=ax)

        ax.set_title(f"{ind_name} Comparison")
        ax.set_xlabel("Year")
        ax.xaxis.set_major_locator(plt.MaxNLocator(integer=True))
        try:
            unit = IndicatorUnits[ind_id].value
        except KeyError:
            unit = "Value"
        ax.set_ylabel(f"Value ({unit})")
        ax.grid(True)
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.15), ncol=len(company_names))

    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    buf.close()
    plt.close()
    return img_base64
