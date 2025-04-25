import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

df_all = pd.read_excel("esg_dataset.xlsx")

indicator_units = {
    "IND_001": "tCO2e", "IND_002": "tCO2e", "IND_003": "tCO2e",
    "IND_004": "MWh", "IND_005": "m³/year", "IND_006": "%",
    "IND_007": "Tones", "IND_009": "%", "IND_010": "Metric tons"
}

def plot_company_all_three_categories(company_name):
    indicator_names = {
        "IND_001": "Scope 1 GHG Emissions",
        "IND_002": "Scope 2 GHG Emissions",
        "IND_003": "Scope 3 GHG Emissions",
        "IND_004": "Total energy consumption",
        "IND_005": "Water consumption",
        "IND_006": "Water recycled/reused",
        "IND_007": "Total waste generated",
        "IND_009": "Product packaging recyclability",
        "IND_010": "Packaging"
    }

    category_map = {
        "Climate / Emissions": ["IND_001", "IND_002", "IND_003"],
        "Energy": ["IND_004", "IND_005", "IND_006"],
        "Waste": ["IND_007", "IND_009", "IND_010"]
    }

    for category, indicator_ids in category_map.items():
        df_cat = df_all[(df_all["company_name"] == company_name) & (df_all["indicator_id"].isin(indicator_ids))]

        if any(indicator_units.get(iid) == "%" for iid in indicator_ids):
            fig, ax1 = plt.subplots(figsize=(10, 5))
            ax2 = ax1.twinx()
            all_handles, all_labels = [], []

            for ind_id in indicator_ids:
                sub_df = df_cat[df_cat["indicator_id"] == ind_id]
                if sub_df.empty:
                    continue

                base_label = indicator_names.get(ind_id, ind_id)
                label = base_label
                if base_label not in ["Water recycled/reused", "Product packaging recyclability"]:
                    label += f" ({indicator_units[ind_id]})"

                if indicator_units[ind_id] == "%":
                    line = sns.lineplot(x="year", y="value", data=sub_df, ax=ax2, marker="o", linestyle="--", label=label)
                else:
                    line = sns.lineplot(x="year", y="value", data=sub_df, ax=ax1, marker="o", label=label)

                all_handles.append(line.lines[0])
                all_labels.append(label)

            ax1.set_ylabel("Value (Non-Percentage Units)")
            ax2.set_ylabel("Value (%)")
            ax1.set_title(f"{company_name} - {category}")
            ax1.set_xlabel("Year")
            ax1.xaxis.set_major_locator(plt.MaxNLocator(integer=True))

            if ax2.legend_:
                ax2.legend_.remove()

            ax1.legend(handles=all_handles, labels=all_labels, loc="upper center", bbox_to_anchor=(0.5, -0.15), ncol=2)
            ax1.grid(True)
            fig.tight_layout()
            plt.show()

        else:
            plt.figure(figsize=(10, 5))
            for ind_id in indicator_ids:
                sub_df = df_cat[df_cat["indicator_id"] == ind_id]
                if not sub_df.empty:
                    label = indicator_names.get(ind_id, ind_id)
                    sns.lineplot(x="year", y="value", data=sub_df, label=label, marker="o")

            ax = plt.gca()
            ax.set_title(f"{company_name} - {category}")
            ax.set_xlabel("Year")
            ax.xaxis.set_major_locator(plt.MaxNLocator(integer=True))

            if category == "Climate / Emissions":
                ax.set_ylabel("Value (tCO2e)")
            else:
                ax.set_ylabel("Value")

            ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.15), ncol=2)
            ax.grid(True)
            plt.tight_layout()
            plt.show()

def compare_companies_metrics(company_names, indicators):
    id_to_name = {
        "IND_001": "Scope 1 GHG Emissions",
        "IND_002": "Scope 2 GHG Emissions",
        "IND_003": "Scope 3 GHG Emissions",
        "IND_004": "Total energy consumption",
        "IND_005": "Water consumption",
        "IND_006": "Water recycled/reused",
        "IND_007": "Total waste generated",
        "IND_009": "Product packaging recyclability",
        "IND_010": "Packaging"
    }
    name_to_id = {v: k for k, v in id_to_name.items()}

    indicator_ids = []
    for i in indicators:
        if i in id_to_name:
            indicator_ids.append(i)
        elif i in name_to_id:
            indicator_ids.append(name_to_id[i])
        else:
            print(f"Unknown indicator: {i}")

    for ind_id in indicator_ids:
        ind_name = id_to_name.get(ind_id, ind_id)
        df_plot = df_all[(df_all["company_name"].isin(company_names)) & (df_all["indicator_id"] == ind_id)]

        if df_plot.empty:
            print(f"No data for: {ind_name}")
            continue

        plt.figure(figsize=(10, 5))
        for company in company_names:
            df_c = df_plot[df_plot["company_name"] == company]
            if not df_c.empty:
                sns.lineplot(x="year", y="value", data=df_c, marker="o", label=company)

        plt.title(f"{ind_name} Comparison")
        plt.xlabel("Year")
        plt.gca().xaxis.set_major_locator(plt.MaxNLocator(integer=True))
        unit = indicator_units.get(ind_id, "Value")
        plt.ylabel(f"Value ({unit})")
        plt.legend(loc="upper center", bbox_to_anchor=(0.5, -0.15), ncol=len(company_names))
        plt.grid(True)
        plt.tight_layout()
        plt.show()

plot_company_all_three_categories("Apple")
compare_companies_metrics(["Apple", "Google", "Amazon"], ["Scope 1 GHG Emissions", "Scope 2 GHG Emissions", "IND_009"])
