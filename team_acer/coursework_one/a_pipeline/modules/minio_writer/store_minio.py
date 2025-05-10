import boto3
from botocore.exceptions import ClientError
import os

# =============================
#        CONFIGURATION
# =============================

def _init_(self, name, age):
    self.name = name
    self.age = age

MINIO_ENDPOINT = "http://localhost:9000"
MINIO_ACCESS_KEY = "ift_bigdata"
MINIO_SECRET_KEY = "minio_password"
BUCKET_NAME = "csr-reports"

# MinIO Client
minio_client = boto3.client(
    "s3",
    endpoint_url=MINIO_ENDPOINT,
    aws_access_key_id=MINIO_ACCESS_KEY,
    aws_secret_access_key=MINIO_SECRET_KEY,
)

# =============================
#   CREATE BUCKET IF NOT EXISTS
# =============================

def ensure_minio_bucket():
    """Check if MinIO bucket exists, and create it if it does not."""
    try:
        existing_buckets = [bucket["Name"] for bucket in minio_client.list_buckets()["Buckets"]]
        if BUCKET_NAME not in existing_buckets:
            print(f"🚀 Creating MinIO bucket: {BUCKET_NAME}...")
            minio_client.create_bucket(Bucket=BUCKET_NAME)
            print(f"✅ MinIO bucket '{BUCKET_NAME}' created successfully.")
        else:
            print(f"✅ MinIO bucket '{BUCKET_NAME}' already exists.")
    except ClientError as e:
        print(f"❌ MinIO Bucket Error: {e}")

# Ensure bucket exists before performing any operations
ensure_minio_bucket()

# =============================
#   CHECK IF REPORT EXISTS
# =============================

def check_minio_exists(region, country, sector, industry, security, year):
    """
    Checks if a CSR report already exists in MinIO.
    
    Args:
        region (str): Company region.
        country (str): Company country.
        sector (str): Company sector.
        industry (str): Company industry.
        security (str): Company security name.
        year (int): Report year.

    Returns:
        bool: True if report exists, False otherwise.
    """
    minio_key = f"{region}/{country}/{sector}/{industry}/{security}/{year}/{security}_CSR_{year}.pdf"

    try:
        minio_client.head_object(Bucket=BUCKET_NAME, Key=minio_key)
        return True  # ✅ Report exists
    except ClientError:
        return False  # ❌ Report does not exist


# =============================
#   UPLOAD REPORT TO MINIO
# =============================

def upload_to_minio(file_path, region, country, sector, industry, security, year):
    """
    Uploads a CSR report to MinIO with structured folder hierarchy.

    Args:
        file_path (str): Path of the file to upload.
        region (str): Company region.
        country (str): Company country.
        sector (str): Company sector.
        industry (str): Company industry.
        security (str): Security name.
        year (int): Report year.

    Returns:
        str: URL of uploaded file in MinIO or None if failed.
    """
    minio_key = f"{region}/{country}/{sector}/{industry}/{security}/{year}/{security}_CSR_{year}.pdf"

    # Check if file already exists
    if check_minio_exists(region, country, sector, industry, security, year):
        print(f"⚠️ File already exists in MinIO: {minio_key}. Skipping upload.")
        return f"{MINIO_ENDPOINT}/{BUCKET_NAME}/{minio_key}"

    try:
        minio_client.upload_file(file_path, BUCKET_NAME, minio_key)
        minio_url = f"{MINIO_ENDPOINT}/{BUCKET_NAME}/{minio_key}"
        print(f"✅ Uploaded to MinIO: {minio_url}")
        return minio_url
    except ClientError as e:
        print(f"❌ MinIO Upload Error: {e}")
        return None