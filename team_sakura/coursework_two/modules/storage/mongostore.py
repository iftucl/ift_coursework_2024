from pymongo import MongoClient, ASCENDING, UpdateOne
import os
import yaml

# Load environment variables and configuration file
config_path = os.getenv("CONF_PATH", "coursework_one/a_pipeline/config/conf.yaml")
with open(config_path, "r") as file:
    config = yaml.safe_load(file)

# Determine which MongoDB configuration to use (Docker or local environment)
if os.getenv("DOCKER_ENV"):
    mongo_config = config["databasedocker"]
else:
    mongo_config = config["databaselocal"]

# Mapping of indicator names to thematic areas
THEMATIC_MAPPING = {
    "Scope 1 Emissions": "Greenhouse Gas Emissions",
    "Scope 2 Emissions": "Greenhouse Gas Emissions",
    "Scope 3 Emissions": "Greenhouse Gas Emissions",
    "Total GHG Emissions": "Greenhouse Gas Emissions",
    "GHG Intensity": "Greenhouse Gas Emissions",
    "Total Water Withdrawal": "Water Usage",
    "Total Water Consumption": "Water Usage",
    "Water Recycled": "Water Usage",
    "Water Intensity": "Water Usage",
    "Total Energy Consumption": "Energy",
    "Renewable Energy Consumption": "Energy",
    "Renewable Energy Percentage": "Energy",
    "Energy Intensity": "Energy",
    "Total Waste Generated": "Waste & Recycling",
    "Waste Recycled Generated": "Waste & Recycling",
    "Waste Recycled Percentage": "Waste & Recycling",
    "Hazardous Waste": "Waste & Recycling"
}


def initialize_indicators_database():
    """
    Initialize the MongoDB connection and ensure necessary indexes exist.

    Returns:
        pymongo.collection.Collection: The MongoDB collection object.
    """
    client = MongoClient(mongo_config["mongo_uri"])
    db = client[mongo_config["mongo_db"]]
    collection = db["sustainability_indicators"]

    # Create unique index to prevent duplicate entries for the same company, year, and indicator
    collection.create_index(
        [("company_name", ASCENDING), ("report_year", ASCENDING), ("indicator_name", ASCENDING)],
        name="company_year_indicator_index",
        unique=True
    )

    # Additional indexes to optimize queries by thematic area and report year
    collection.create_index("thematic_area")
    collection.create_index("report_year")

    print(f" Collection '{collection.name}' initialized with indexes.")
    return collection


def save_indicators_to_mongo(company_name, report_year, indicators_list, collection, max_batch_size=500):
    """
    Save a list of indicators to MongoDB.

    Args:
        company_name (str): Name of the company.
        report_year (int): Reporting year of the indicators.
        indicators_list (list): List of indicator dictionaries to insert or update.
        collection (pymongo.collection.Collection): The MongoDB collection object.
        max_batch_size (int): Maximum number of operations per bulk write.
    """
    if not indicators_list:
        print("️ No indicators to insert.")
        return

    bulk_operations = []  # List to hold bulk operations
    bulk_info_list = []  # List to hold operation metadata for logging

    for indicator in indicators_list:
        indicator_name = indicator.get("indicator_name")
        filter_query = {
            "company_name": company_name,
            "report_year": report_year,
            "indicator_name": indicator_name
        }

        # Check if the document already exists
        exists = collection.find_one(filter_query) is not None

        # Log whether this will be an insert or update operation
        bulk_info_list.append({
            "company_name": company_name,
            "report_year": report_year,
            "indicator_name": indicator_name,
            "operation": "Updated" if exists else "Inserted"
        })

        # Sanitize the value (convert to float if possible or set to None)
        raw_value = indicator.get("value")
        if raw_value is None or (
            isinstance(raw_value, str) and raw_value.strip().lower() in ["n/a", "not reported", ""]):
            value = None
        elif isinstance(raw_value, str):
            try:
                value = float(raw_value.replace(",", ""))
            except ValueError:
                value = None
        else:
            value = raw_value

        # Prepare the document for insertion/updating
        ordered_doc = {
            "company_name": company_name,
            "report_year": report_year,
            "indicator_name": indicator_name,
            "thematic_area": THEMATIC_MAPPING.get(indicator_name, "Unknown"),
            "value": value,
            "unit": indicator.get("unit"),
            "normalized_value": indicator.get("normalized_value"),
            "normalized_unit": indicator.get("normalized_unit"),
        }

        # Prepare the UpdateOne operation with upsert enabled
        update_op = UpdateOne(
            filter_query,
            {"$set": ordered_doc},
            upsert=True
        )
        bulk_operations.append(update_op)

        # Commit the batch when max_batch_size is reached
        if len(bulk_operations) >= max_batch_size:
            _commit_bulk_batch(collection, bulk_operations, bulk_info_list)
            bulk_operations.clear()
            bulk_info_list.clear()

    # Commit any remaining operations after the loop
    if bulk_operations:
        _commit_bulk_batch(collection, bulk_operations, bulk_info_list)


def _commit_bulk_batch(collection, operations, info_list):
    """
    Helper function to commit a batch of bulk operations and log results.

    Args:
        collection (pymongo.collection.Collection): The MongoDB collection object.
        operations (list): List of bulk write operations.
        info_list (list): Metadata for logging insert/update operations.
    """
    try:
        result = collection.bulk_write(operations, ordered=True)
        print(f" Batch write completed: {result.modified_count} updated, {result.upserted_count} inserted.")

        # Log each operation (Inserted/Updated)
        for info in info_list:
            print(f" {info['operation']}: {info['company_name']} ({info['report_year']}) - {info['indicator_name']}")
    except Exception as e:
        print(f" Error during batch bulk write: {e}")


def reset_indicators_collection():
    """
    Drops all documents in the sustainability_indicators collection, resetting it.
    """
    collection = initialize_indicators_database()
    deleted_count = collection.delete_many({}).deleted_count
    print(f" Collection reset completed. {deleted_count} documents deleted.")
