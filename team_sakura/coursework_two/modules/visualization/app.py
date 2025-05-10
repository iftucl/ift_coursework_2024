from flask import Flask, render_template, request
from pymongo import MongoClient
from utils.db import get_all_indicators
import os
import yaml

app = Flask(__name__)

# Load MongoDB configuration from environment or fallback to local config file
config_path = os.getenv("CONF_PATH", "coursework_one/a_pipeline/config/conf.yaml")
with open(config_path, "r") as file:
    config = yaml.safe_load(file)

mongo_config = config["databaselocal"]
client = MongoClient(mongo_config["mongo_uri"])
db = client[mongo_config["mongo_db"]]
collection = db["sustainability_indicators"]


@app.route("/")
def index():
    """
    Render the dashboard page.

    Accepts optional query parameters:
    - company (str): Filter indicators by company name.
    - year (str or int): Filter indicators by report year.

    Returns:
        Rendered HTML page (dashboard.html) with filtered indicators.
    """
    company = request.args.get("company")
    year = request.args.get("year")
    indicators = get_all_indicators(company=company, year=year)
    return render_template("dashboard.html", indicators=indicators)


@app.route("/plot", methods=["GET"])
def plot():
    """
    Render the plotting selection page.

    Allows user to select a company and an indicator, then shows corresponding yearly data.

    Query parameters:
    - company (str): Selected company name to plot indicators for.
    - indicator (str): Selected indicator name to plot values over years.

    Returns:
        Rendered HTML page (select.html) with plot data (years and values).
    """
    companies = collection.distinct("company_name")
    indicators = collection.distinct("indicator_name")

    company = request.args.get("company")
    indicator_name = request.args.get("indicator")

    years = []
    values = []

    # If both company and indicator are selected, fetch records and prepare data for plotting
    if company and indicator_name:
        records = collection.find({
            "company_name": company,
            "indicator_name": indicator_name
        }).sort("report_year", 1)

        for record in records:
            years.append(record.get("report_year"))
            values.append(record.get("value"))

    return render_template("select.html",
                           companies=companies,
                           indicators=indicators,
                           selected_company=company,
                           selected_indicator=indicator_name,
                           years=years,
                           values=values)


if __name__ == "__main__":
    app.run(debug=True)
