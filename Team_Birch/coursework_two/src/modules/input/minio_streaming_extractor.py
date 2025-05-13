"""
Streams PDF files from MinIO storage and triggers CSR indicator extraction.
"""

import logging
import os
from io import BytesIO
from pathlib import Path

from dotenv import load_dotenv
from minio import Minio

from modules.input.emissions_parser import extract_indicators_from_bytes

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def connect_to_minio_from_env():
    """
    Connects to MinIO server using environment variables.

    Returns:
        Minio: Connected MinIO client object.
    """
    return Minio(
        os.getenv("MINIO_ENDPOINT"),
        access_key=os.getenv("MINIO_ACCESS_KEY"),
        secret_key=os.getenv("MINIO_SECRET_KEY"),
        secure=os.getenv("MINIO_SECURE", "false").lower() == "true",
    )


def stream_pdf_and_extract(
    minio_client, bucket, config_path, output_csv, log_path, prefix=""
):
    """
    Streams PDF files from a MinIO bucket, extracts CSR indicators, and saves results.

    Args:
        minio_client (Minio): Initialized MinIO client.
        bucket (str): Bucket name containing CSR PDF reports.
        config_path (Path): Path to indicators YAML configuration.
        output_csv (Path): Path to save extracted results.
        log_path (Path): Path to save extraction log.
        prefix (str, optional): Object prefix filter inside bucket. Defaults to "".

    Returns:
        None
    """
    config_path = Path(config_path)
    output_csv = Path(output_csv)
    log_path = Path(log_path)

    if not config_path.exists():
        raise FileNotFoundError(f"Config path not found: {config_path}")

    for obj in minio_client.list_objects(bucket, prefix=prefix, recursive=True):
        if not obj.object_name.endswith(".pdf"):
            continue

        company = Path(obj.object_name).stem
        logger.info(f"Processing: {company}")

        try:
            response = minio_client.get_object(bucket, obj.object_name)
            buffer = BytesIO(response.read())
            response.close()
            response.release_conn()

            extract_indicators_from_bytes(
                company_name=company,
                pdf_bytes=buffer,
                config_path=config_path,
                output_csv=output_csv,
                log_path=log_path,
                source_filename=Path(obj.object_name).name,
            )

            logger.info(f"Parsed: {company}")
        except Exception as e:
            logger.error(f"Failed to process {company} ({obj.object_name}): {e}")
