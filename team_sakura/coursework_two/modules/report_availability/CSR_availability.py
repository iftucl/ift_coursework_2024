import os
import pymongo
from dotenv import load_dotenv
import yaml

# Load environment variables from .env file
load_dotenv()

# Load configuration file for MongoDB settings
config_path = os.getenv("CONF_PATH", "coursework_one/a_pipeline/config/conf.yaml")
with open(config_path, "r") as file:
    config = yaml.safe_load(file)

# Select appropriate MongoDB configuration based on environment (Docker or local)
mongo_config = config["databaselocal"] if not os.getenv("DOCKER_ENV") else config["databasedocker"]

def get_mongo_collection():
    """
    Initialize and return the MongoDB collection object.

    Returns:
        pymongo.collection.Collection: The MongoDB collection instance.
    """
    mongo_client = pymongo.MongoClient(mongo_config["mongo_uri"])
    db = mongo_client[mongo_config["mongo_db"]]
    collection = db[mongo_config["mongo_collection"]]
    return collection

def check_report_in_mongo(company_name, report_year):
    """
    Check if a CSR report exists in the MongoDB collection for a given company and report year.

    Args:
        company_name (str): Name of the company to search for (case insensitive).
        report_year (int or str): The year of the report to search for.

    Returns:
        bool: True if the report exists, False otherwise.
    """
    collection = get_mongo_collection()

    query = {
        "company_name": {"$regex": f"^{company_name}$", "$options": "i"},
        "report_year": str(report_year)
    }

    report = collection.find_one(query)
    print(f"MongoDB query: {query} → Found: {report is not None}")
    return report is not None

def check_csr_report(company_name, report_year):
    """
    Alias for check_report_in_mongo for checking CSR report availability.

    Args:
        company_name (str): Company name.
        report_year (int or str): Report year.

    Returns:
        bool: True if the CSR report exists, False otherwise.
    """
    return check_report_in_mongo(company_name, report_year)

# CLI entry point to manually check for CSR report availability
if __name__ == "__main__":
    import argparse
    import time

    parser = argparse.ArgumentParser(description="Check CSR report availability in MongoDB.")
    parser.add_argument("--company", required=True, help="Company name")
    parser.add_argument("--year", required=True, type=int, help="Report year")
    parser.add_argument("--retries", type=int, default=1, help="Number of retries if not found")
    parser.add_argument("--interval", type=int, default=5, help="Wait time between retries (seconds)")
    args = parser.parse_args()

    # Retry mechanism to repeatedly check for report availability
    for attempt in range(args.retries):
        if check_csr_report(args.company, args.year):
            print(f"The CSR report for {args.company} ({args.year}) is available in the data lake.")
            break
        else:
            print(f"[{attempt + 1}/{args.retries}] Report not found... retrying in {args.interval} seconds.")
            time.sleep(args.interval)
    else:
        print(f"No CSR report found for {args.company} ({args.year}) after {args.retries} retries.")
