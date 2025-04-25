"""
Utility functions for integrating OpenMetadata metadata management.

https://docs.open-metadata.org/latest/sdk/python

TODO:
- Create script to register sql tables in OpenMetadata
- Create script to register Minio buckets in OpenMetadata
- Create script to register Minio files in OpenMetadata
- Create script to register MongoDB documents in OpenMetadata
- Fix docker compose to get UI working
"""

import os
from openmetadata.ingestion.ometa.ometa_api import OpenMetadata
from openmetadata.ingestion.models.table_metadata import CreateTableRequest, Column
from openmetadata.ingestion.models.database import DatabaseServiceEntity, CreateDatabaseRequest
from openmetadata.ingestion.models.database_schema import CreateDatabaseSchemaRequest
from openmetadata.ingestion.models.table_metadata import Table

def get_metadata_client():
    """
    Initialize and return an OpenMetadata client using environment variables.
    """
    server_url = os.getenv("OPENMETADATA_SERVER_URL", "http://localhost:8585/api")
    auth_provider = os.getenv("OPENMETADATA_AUTH_PROVIDER", "no-auth")
    auth_token = os.getenv("OPENMETADATA_AUTH_TOKEN", "")

    config = {
        "api_endpoint": server_url,
        "auth_provider_type": auth_provider,
        "auth_token": auth_token,
    }
    return OpenMetadata(config)

def register_table_metadata(
    metadata: OpenMetadata,
    service_name: str,
    database_name: str,
    schema_name: str,
    table_name: str,
    description: str = "",
    columns: list = None
):
    """
    Register a table and its metadata in OpenMetadata.

    Args:
        metadata: OpenMetadata client instance.
        service_name: Name of the database service in OpenMetadata.
        database_name: Name of the database.
        schema_name: Name of the schema.
        table_name: Name of the table.
        description: Table description.
        columns: List of Column objects (optional).
    """
    # Ensure the database service exists (create if not)
    service = metadata.get_by_name(DatabaseServiceEntity, service_name)
    if not service:
        raise ValueError(f"Database service '{service_name}' not found in OpenMetadata.")

    # Ensure the database exists (create if not)
    db_fqn = f"{service_name}.{database_name}"
    database = metadata.get_by_name(CreateDatabaseRequest, db_fqn)
    if not database:
        db_request = CreateDatabaseRequest(
            name=database_name,
            service=service.fullyQualifiedName
        )
        database = metadata.create_or_update(db_request)

    # Ensure the schema exists (create if not)
    schema_fqn = f"{service_name}.{database_name}.{schema_name}"
    schema = metadata.get_by_name(CreateDatabaseSchemaRequest, schema_fqn)
    if not schema:
        schema_request = CreateDatabaseSchemaRequest(
            name=schema_name,
            database=database.fullyQualifiedName
        )
        schema = metadata.create_or_update(schema_request)

    # Register the table
    table_request = CreateTableRequest(
        name=table_name,
        databaseSchema=schema.fullyQualifiedName,
        description=description,
        columns=columns or []
    )
    table = metadata.create_or_update(table_request)
    print(f"Registered table: {table.fullyQualifiedName}")
    return table

def get_table_metadata(metadata: OpenMetadata, fqn: str):
    """
    Retrieve metadata for a table by its fully qualified name (FQN).
    """
    table = metadata.get_by_name(Table, fqn)
    return table

# Example: Define columns for a table
def example_column_list():
    return [
        Column(name="id", dataType="INT", description="Primary key"),
        Column(name="name", dataType="STRING", description="Name field"),
    ]
