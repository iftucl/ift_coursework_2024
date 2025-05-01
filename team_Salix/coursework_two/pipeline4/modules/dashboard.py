import pandas as pd
import streamlit as st
from sqlalchemy import create_engine

# PostgreSQL connection configuration
DB_HOST = "localhost"
DB_PORT = "5439"
DB_NAME = "fift"
DB_USER = "postgres"
DB_PASSWORD = "postgres"

# Construct connection string
DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Create SQLAlchemy engine
engine = create_engine(DATABASE_URL)

# Streamlit page config
st.set_page_config(page_title="ESG & Data Lineage Dashboard", layout="wide")
st.title("📊 ESG & Data Lineage Dashboard")


# Load ESG data
@st.cache_data
def load_esg_data():
    """
    Load ESG indicators data from PostgreSQL database.

    Returns:
        pd.DataFrame: DataFrame containing ESG indicators data

    This function:
    1. Queries the 'esg_indicators' table in the 'csr_reporting' schema
    2. Returns the data as a pandas DataFrame
    3. Uses Streamlit's caching to improve performance

    Note:
        The function is decorated with @st.cache_data to cache the results
        and avoid unnecessary database queries.
    """
    query = "SELECT * FROM csr_reporting.esg_indicators"
    return pd.read_sql(query, engine)


# Load Data Lineage data from PostgreSQL
def load_lineage_data():
    """
    Load data lineage information from PostgreSQL database.

    Returns:
        pd.DataFrame: DataFrame containing data lineage information

    This function:
    1. Queries the 'data_lineage' table in the 'csr_reporting' schema
    2. Returns the data as a pandas DataFrame
    3. Includes information about data flow, scripts, and processing steps

    Note:
        The function does not use caching as the lineage data may change
        frequently during pipeline execution.
    """
    query = "SELECT * FROM csr_reporting.data_lineage"
    return pd.read_sql(query, engine)


# Create tabs for different visualizations
tab1, tab2 = st.tabs(["ESG Indicators", "Data Lineage"])

# ESG Indicators Tab
with tab1:
    st.header("ESG Indicators Analysis")

    df_esg = load_esg_data()

    if df_esg.empty:
        st.warning("No ESG data available. Please ensure write_to_db.py was executed successfully.")
    else:
        # Dropdown filters
        companies = sorted(df_esg["company"].dropna().unique())
        years = sorted(df_esg["year"].dropna().unique())

        col1, col2 = st.columns(2)
        with col1:
            selected_companies = st.multiselect("Select company", companies, default=companies[:3])
        with col2:
            selected_years = st.multiselect("Select year", years, default=years)

        # Filter the data
        filtered_df = df_esg[df_esg["company"].isin(selected_companies) & df_esg["year"].isin(selected_years)]

        # Display table
        st.subheader("🧾 ESG Data Table")
        st.dataframe(filtered_df, use_container_width=True)

        # Select indicator for visualization
        numeric_columns = [
            "scope1_emissions",
            "scope2_emissions",
            "total_energy_consumption",
            "total_water_withdrawal",
            "total_waste_generated",
            "employee_diversity",
        ]

        selected_metric = st.selectbox("Select ESG indicator for visualization", numeric_columns)

        st.subheader(f"📈 Trend of {selected_metric.replace('_', ' ').title()}")

        # Line chart for selected indicator
        for company in selected_companies:
            company_data = filtered_df[filtered_df["company"] == company]
            chart_data = company_data[["year", selected_metric]].dropna()

            if chart_data.empty:
                st.info(f"No data for {company} and {selected_metric} in the selected years.")
                continue

            st.line_chart(chart_data.set_index("year"), height=300, use_container_width=True)

# Data Lineage Tab
with tab2:
    st.header("Data Lineage Analysis")

    df_lineage = load_lineage_data()

    if df_lineage.empty:
        st.warning("No data lineage information available. Please ensure write_lineage.py was executed successfully.")
    else:
        # Display all column names for debugging
        st.write("Columns:", df_lineage.columns.tolist())

        # Display complete table
        st.subheader("🧾 Data Lineage Table")
        st.dataframe(df_lineage, use_container_width=True)

        # Distribution statistics using Script column
        if "Script" in df_lineage.columns:
            st.subheader("📊 Script Distribution")
            script_counts = df_lineage["Script"].value_counts()
            st.bar_chart(script_counts)

        # Distribution statistics using Input column
        if "Input" in df_lineage.columns:
            st.subheader("📊 Input File Distribution")
            input_counts = df_lineage["Input"].value_counts()
            st.bar_chart(input_counts)

        # Data flow visualization
        if (
            "Input" in df_lineage.columns
            and "Output" in df_lineage.columns
            and "Script" in df_lineage.columns
            and "Processing" in df_lineage.columns
        ):
            st.subheader("🔄 Data Flow")
            for _, row in df_lineage.iterrows():
                st.write(f"**{row['Input']}** ➡️ **{row['Output']}** (by `{row['Script']}`)")
                st.caption(f"Processing: {row['Processing']}")
