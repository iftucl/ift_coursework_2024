# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

# create db by excel file


import copy
import csv  # Added csv import

import numpy as np
import pandas as pd
from theme_pixel.models import (
    AirPollution,
    AirPollutionData,
    CompanyReport,
    CompanyReportData,
)


def init():
    with open("static/data.xlsx", "rb") as f:
        df = pd.read_excel(f, sheet_name="Text", header=0)
        df2 = pd.read_excel(f, sheet_name="Data", header=None)

    # delete #N/A Invalid Security
    df = df[df["ISIN"] != "#N/A Invalid Security"]

    # cache npy file
    df.to_pickle("static/data.npy")

    dfNew = pd.DataFrame(columns=["Ticker", "dates"])
    df2Shape = df2.shape

    for i in range(df2Shape[0]):
        if df2.iloc[i, 1] == "Dates":
            ticker = df2.iloc[i, 0]
            dictLine = {}
            for j in range(2, df2Shape[1]):
                if pd.isnull(df2.iloc[i, j]):
                    break
                if df2.iloc[i, j] == "#N/A Review":
                    break
                try:
                    dates = pd.to_datetime(
                        int(df2.iloc[i, j]), unit="D", origin="1899-12-30"
                    )
                except:
                    dates = df2.iloc[i, j]
                dictLine["dates"] = dates
                k = 1
                while pd.notnull(df2.iloc[i + k, 1]):
                    dictLine[df2.iloc[i + k, 1]] = df2.iloc[i + k, j]
                    k += 1
                    if i + k >= len(df2):
                        break
                dictLine["Ticker"] = ticker
                dfNew = dfNew._append(copy.deepcopy(dictLine), ignore_index=True)
                dictLine.clear()

    # cache npy file with header
    dfNew.to_pickle("static/dataNew.npy")


def load_data():
    # load npy file to dataframe
    data1 = np.load("static/data.npy", allow_pickle=True)
    data2 = np.load("static/dataNew.npy", allow_pickle=True)
    data1 = pd.DataFrame(data1)
    data2 = pd.DataFrame(data2)

    # aList = []
    # for index, row in data1.iterrows():

    #     a = AirPollution(
    #         ISIN=row['ISIN'],
    #         CompanyName=row['Company Name'],
    #         Country = row['Country'],
    #         Industry=row['Industry'],
    #         Ticker=row['Ticker']
    #     )
    #     aList.append(a)
    # AirPollution.objects.bulk_create(aList)

    bList = []
    for index, row in data2.iterrows():
        try:
            b = AirPollutionData(
                airPollution=AirPollution.objects.get(Ticker=row["Ticker"]),
                dates=row["dates"],
                GHG_SCOPE_1=row["GHG_SCOPE_1"],
                GHG_SCOPE_2_LOCATION_BASED=row["GHG_SCOPE_2_LOCATION_BASED"],
                GHG_SCOPE_2_MARKET_BASED=row["GHG_SCOPE_2_MARKET_BASED"],
                CO2_SCOPE_1=row["CO2_SCOPE_1"],
                CO2_SCOPE_2_LOCATION_BASED=row["CO2_SCOPE_2_LOCATION_BASED"],
                CO2_SCOPE_2_MARKET_BASED=row["CO2_SCOPE_2_MARKET_BASED"],
                SCOPE_2_GHG_CO2_EMISSIONS=row["SCOPE_2_GHG_CO2_EMISSIONS"],
                SCOPE_1_GHG_CO2_EMISSIONS=row["SCOPE_1_GHG_CO2_EMISSIONS"],
            )
            bList.append(b)
        except:
            print(row["Ticker"])
            continue

    AirPollutionData.objects.bulk_create(bList)


# init()
# load_data()


def load_company_report_data():
    """Loads data from UI_data.csv into the CompanyReportData model."""
    data_to_insert = []
    csv_file_path = "UI_data.csv"  # Assuming the CSV is in the same directory or provide the full path

    try:
        with open(csv_file_path, mode="r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                # Helper function to convert empty strings or specific markers to None, and handle type conversion
                def clean_value(value, target_type=str):
                    if value is None or value.strip() == "":
                        return None
                    try:
                        if target_type == float:
                            return float(value)
                        elif target_type == int:
                            return int(value)
                        else:
                            # Limit string length if necessary, e.g., for report_url
                            if (
                                len(value) > 500 and target_type == str
                            ):  # Example limit for URL
                                return value[:500]
                            return value
                    except ValueError:
                        print(
                            f"Warning: Could not convert '{value}' to {target_type}. Skipping row or setting to None."
                        )
                        return None  # Or handle error as appropriate

                report_data = CompanyReportData(
                    symbol=clean_value(row.get("symbol")),
                    security=clean_value(row.get("security")),
                    gics_sector=clean_value(row.get("gics_sector")),
                    gics_industry=clean_value(row.get("gics_industry")),
                    country=clean_value(row.get("country")),
                    region=clean_value(row.get("region")),
                    report_url=clean_value(row.get("report_url")),
                    report_year=clean_value(row.get("report year"), int),
                    annual_carbon_emissions=clean_value(
                        row.get("annual carbon emissions (tonnes co₂)"), float
                    ),
                    annual_water_consumption=clean_value(
                        row.get("annual water consumption (cubic meters)"), float
                    ),
                    renewable_energy_usage=clean_value(
                        row.get("renewable energy usage (mwh)"), float
                    ),
                    sustainable_materials_usage_ratio=clean_value(
                        row.get("sustainable materials usage ratio (percent)"), float
                    ),
                    waste_recycling_rate=clean_value(
                        row.get("waste recycling rate (percent)"), float
                    ),
                )
                data_to_insert.append(report_data)

        if data_to_insert:
            CompanyReportData.objects.bulk_create(
                data_to_insert, ignore_conflicts=True
            )  # Use ignore_conflicts if duplicates should be skipped
            print(
                f"Successfully inserted {len(data_to_insert)} records from {csv_file_path}"
            )
        else:
            print("No data to insert.")

    except FileNotFoundError:
        print(f"Error: The file {csv_file_path} was not found.")
    except Exception as e:
        print(f"An error occurred: {e}")


# Function to load unique company info into CompanyReport model
def load_company_report():
    """Loads unique company data from UI_data.csv into the CompanyReport model."""
    companies_to_insert = []
    seen_securities = set()
    csv_file_path = "UI_data.csv"

    try:
        with open(csv_file_path, mode="r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                security = row.get("security")
                if security and security not in seen_securities:
                    # Helper function to clean values (similar to load_company_report_data)
                    def clean_value(value):
                        return value.strip() if value else None

                    company_info = CompanyReport(
                        symbol=clean_value(row.get("symbol")),
                        security=clean_value(security),
                        gics_sector=clean_value(row.get("gics_sector")),
                        gics_industry=clean_value(row.get("gics_industry")),
                        country=clean_value(row.get("country")),
                        region=clean_value(row.get("region")),
                    )
                    companies_to_insert.append(company_info)
                    seen_securities.add(security)

        if companies_to_insert:
            # Use ignore_conflicts=True to avoid errors if a security already exists (e.g., if run multiple times)
            CompanyReport.objects.bulk_create(
                companies_to_insert, ignore_conflicts=True
            )
            print(
                f"Successfully inserted/updated {len(companies_to_insert)} unique companies into CompanyReport from {csv_file_path}"
            )
        else:
            print("No new unique companies found to insert.")

    except FileNotFoundError:
        print(f"Error: The file {csv_file_path} was not found.")
    except Exception as e:
        print(f"An error occurred while loading company reports: {e}")


# Uncomment the lines below to run the functions
# Make sure Django environment is set up (e.g., run within `python manage.py shell`)
# import dbcreate
# dbcreate.load_company_report()
# dbcreate.load_company_report_data()

# Example command to run from shell:
# python manage.py shell -c 'import dbcreate; dbcreate.load_company_report(); dbcreate.load_company_report_data()'
