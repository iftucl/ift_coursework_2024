# CSR Cleanup Tool: Fixes and enhances metadata for collected CSR reports
# - Extracts actual report years from PDF content
# - Standardizes data formats across records
# - Removes duplicate reports to save storage
import os
import re
import datetime
import pdfplumber
import magic
from pymongo import MongoClient
from minio import Minio

# ========== Configuration ==========
# MongoDB connection settings for metadata storage
# Auto-detect if we're running in Docker or locally
if os.environ.get("DOCKER_ENV") == "true":
    # In Docker container
    MONGO_URI = os.environ.get("MONGO_URI", "mongodb://mongo_db:27017")
else:
    # Local development
    MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27019")

MONGO_DB_NAME = "csr_db"
MONGO_COLLECTION = "csr_reports"

# MinIO connection for accessing PDF files
# Auto-detect if we're running in Docker or locally
if os.environ.get("DOCKER_ENV") == "true":
    # In Docker container
    MINIO_HOST = os.environ.get("MINIO_HOST", "miniocw:9000")
else:
    # Local development
    MINIO_HOST = os.environ.get("MINIO_HOST", "localhost:9000")

MINIO_CLIENT = Minio(
    MINIO_HOST,
    access_key="ift_bigdata",
    secret_key="minio_password",
    secure=False,
)
BUCKET_NAME = "csreport"

# Initialize MongoDB connection
mongo_client = MongoClient(MONGO_URI)
mongo_db = mongo_client[MONGO_DB_NAME]
collection_reports = mongo_db[MONGO_COLLECTION]

# ========== Logging ==========
# Separate log file for cleanup operations
LOG_FILE = "csr_fix_and_cleanup.log"


def write_log(message):
    """Write logs to file and terminal"""
    # Create a timestamp for the log entry
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_msg = f"[{timestamp}] {message}"
    # Print to console for immediate feedback
    print(log_msg)
    # Write to log file for permanent record
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_msg + "\n")


# ========== Utility Functions ==========
def is_valid_pdf(file_path):
    """Check if the file is a valid PDF"""
    # Use python-magic to determine file type based on content
    mime = magic.Magic(mime=True)
    file_type = mime.from_file(file_path)
    # Verify it's actually a PDF (not just named .pdf)
    return file_type == "application/pdf"


def delete_invalid_pdf_from_minio(object_name):
    """Delete a corrupted PDF from MinIO"""
    try:
        # Remove the invalid file from storage
        MINIO_CLIENT.remove_object(BUCKET_NAME, object_name)
        write_log(f"🗑️ Deleted corrupted file: {object_name}")
    except Exception as e:
        # Handle deletion errors
        write_log(f"⚠️ Failed to delete {object_name}: {e}")


def download_pdf_from_minio(object_name, local_path):
    """Download PDF from MinIO and check if it is a valid PDF"""
    try:
        # Get the PDF file from MinIO storage
        MINIO_CLIENT.fget_object(BUCKET_NAME, object_name, local_path)
        # Verify it's a valid PDF file
        if not is_valid_pdf(local_path):
            # Clean up invalid files
            write_log(f"⚠️ {object_name} is not a valid PDF, deleting")
            os.remove(local_path)
            delete_invalid_pdf_from_minio(object_name)
            return False
        return True
    except Exception as e:
        # Handle download errors
        write_log(f"❌ Failed to download {object_name}: {e}")
        return False


def extract_year_from_pdf(file_path):
    """Extract the year from the PDF (only scans the first two pages)"""
    try:
        # Open the PDF file using pdfplumber
        with pdfplumber.open(file_path) as pdf:
            # Only scan first two pages for efficiency
            for page in pdf.pages[:2]:
                text = page.extract_text() or ""
                # Search for a 4-digit year starting with '20'
                match = re.search(r"20\d{2}", text)
                if match:
                    # Convert to integer and return
                    return int(match.group(0))
    except Exception as e:
        # Handle PDF parsing errors
        write_log(f"❌ Failed to parse {file_path}: {e}")
    return None


# ========== Task 1: Fix CSR Report Year ==========
def update_csr_year():
    """Download PDFs from MinIO, extract the year, and update MongoDB"""
    # Get all CSR reports from the database
    reports = collection_reports.find()
    # Create temporary directory for downloaded files
    local_dir = "./reports"
    os.makedirs(local_dir, exist_ok=True)

    # Process each report
    for doc in reports:
        company_name = doc["company_name"]
        object_name = doc["storage_path"]
        # Create safe local filename by replacing slashes
        local_path = os.path.join(local_dir, object_name.replace("/", "_"))

        write_log(f"📥 Processing PDF for {company_name}: {object_name}")
        # Download and validate the PDF
        if not download_pdf_from_minio(object_name, local_path):
            continue  # Skip if download fails or file is not a PDF

        # Extract year from PDF content
        actual_year = extract_year_from_pdf(local_path)
        if actual_year:
            # Update the MongoDB record with correct year
            collection_reports.update_one(
                {"_id": doc["_id"]}, {"$set": {"csr_report_year": actual_year}}
            )
            write_log(f"✅ Updated {company_name} year to {actual_year}")
        else:
            write_log(f"⚠️ Failed to extract year for {company_name}")

        # Clean up temporary file
        if os.path.exists(local_path):
            os.remove(local_path)


# ========== Task 2: Standardize ingestion_time ==========
def fix_ingestion_time():
    """Convert the ingestion_time field to a standardized string format"""
    # Get all CSR reports from the database
    reports = collection_reports.find()
    for doc in reports:
        ingestion_time = doc.get("ingestion_time")
        # Check if the field is a datetime object
        if isinstance(ingestion_time, datetime.datetime):
            # Convert to ISO format string
            collection_reports.update_one(
                {"_id": doc["_id"]},
                {"$set": {"ingestion_time": ingestion_time.isoformat()}},
            )
            write_log(f"✅ Fixed ingestion_time format for {doc['company_name']}")


# ========== Task 3: Remove Duplicate PDFs (Same Company + Same Year) ==========
def delete_duplicate_pdfs():
    """
    If (company_name, csr_report_year) is exactly the same, keep the first occurrence and delete the later files.
    """
    # Get all reports for duplicate analysis
    all_docs = list(collection_reports.find())
    # Track which company+year combinations we've seen
    seen = {}

    for doc in all_docs:
        comp = doc["company_name"]
        year = doc.get("csr_report_year", None)
        obj_path = doc["storage_path"]
        doc_id = doc["_id"]

        # Skip documents without a year
        if year is None:
            continue

        # Create a unique key for each company+year combination
        key = (comp, year)
        if key not in seen:
            # First occurrence - keep this one
            seen[key] = doc_id
        else:
            # Duplicate detected - remove it
            write_log(f"🗑️ Found duplicate: {comp} ({year}), deleting {obj_path}")
            try:
                # Delete the PDF file from MinIO
                MINIO_CLIENT.remove_object(BUCKET_NAME, obj_path)
                write_log(f"✅ Deleted {obj_path}")
            except Exception as e:
                write_log(f"⚠️ Failed to delete {obj_path}: {e}")
            # Delete the metadata from MongoDB
            collection_reports.delete_one({"_id": doc_id})


# ========== Main Program ==========
def main(dry_run=False):
    """Run the three maintenance tasks – year correction, timestamp
    standardisation, and duplicate removal.

    Parameters
    ----------
    dry_run : bool, optional
        If *True* the function logs what **would** happen without making any
        changes to MongoDB or MinIO.  Default is *False* (perform changes).
    """
    write_log("🔍 Starting data cleaning and fixing task...")

    # Dry run mode only simulates changes
    if dry_run:
        write_log("🔎 Running in dry-run mode, no DB changes will be made")

    # 1. Update CSR report year
    if not dry_run:
        write_log("🚀 Correcting CSR report years...")
        update_csr_year()

    # 2. Fix ingestion_time
    if not dry_run:
        write_log("🚀 Fixing ingestion_time fields...")
        fix_ingestion_time()

    # 3. Delete duplicates
    if not dry_run:
        write_log("🚀 Deleting duplicate CSR reports...")
        delete_duplicate_pdfs()

    write_log("✅ All tasks completed!")



if __name__ == "__main__":
    # Run the main function when script is executed directly
    main()
