import os
import yaml
from pymongo import MongoClient

# Load MongoDB configuration from environment variable or fallback to local config file
config_path = os.getenv("CONF_PATH", "coursework_one/a_pipeline/config/conf.yaml")
with open(config_path, "r") as file:
    config = yaml.safe_load(file)

# Determine whether to use Docker or local MongoDB configuration
mongo_conf = config["databasedocker"] if os.getenv("DOCKER_ENV") else config["databaselocal"]

# Initialize MongoDB client and access the sustainability indicators collection
client = MongoClient(mongo_conf["mongo_uri"])
db = client[mongo_conf["mongo_db"]]
collection = db["sustainability_indicators"]


def get_all_indicators(company=None, year=None):
    """
    Retrieve all sustainability indicators from the MongoDB collection.

    Optionally filter results by company name and/or report year.

    Args:
        company (str, optional): The name of the company to filter indicators by.
        year (int or str, optional): The report year to filter indicators by.

    Returns:
        list: A list of documents (dicts) from the MongoDB collection matching the filters.
    """
    query = {}

    # Add filters to the query if parameters are provided
    if company:
        query["company_name"] = company
    if year:
        query["report_year"] = int(year)

    # Execute query and return matching documents as a list
    return list(collection.find(query))
