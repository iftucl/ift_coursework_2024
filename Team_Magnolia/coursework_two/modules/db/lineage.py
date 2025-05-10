# modules/db/lineage.py

import uuid
import datetime
import subprocess
from pymongo import MongoClient
from modules.extract.config_loader import database

# Connect to MongoDB
_client = MongoClient(database["mongo_uri"], serverSelectionTimeoutMS=5000)
_db     = _client[database["mongo_db"]]
_coll   = _db["csr_lineage"]

def _get_git_sha() -> str:
    """
    Retrieve the current Git commit SHA (short form).
    Returns 'unknown' if the command fails.
    """
    try:
        sha = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL
        ).decode().strip()
        return sha
    except Exception:
        return "unknown"

def record_lineage(
    pdf_src: str,
    stats: dict,
    outputs: dict,
    pipeline_version: str = "v0.1.0"
):
    """
    Insert a lineage record into MongoDB.

    Args:
        pdf_src: Path to the PDF file or MinIO object key used in this run.
        run_stats: Dictionary of run metrics (e.g., pages_scanned, run_seconds).
        outputs: Dictionary mapping output names to file paths.
        pipeline_version: Version identifier for the extraction pipeline.
    """
    record = {
        "_run_id":          str(uuid.uuid4()),
        "timestamp":        datetime.datetime.utcnow().isoformat() + "Z",
        "git_commit":       _get_git_sha(),
        "pipeline_version": pipeline_version,
        "input": {
            "source":      "minio" if "/" in pdf_src else "local",
            "path":        pdf_src,
            "bucket":      database.get("minio", {}).get("bucket") if "/" in pdf_src else None,
        },
        "output_files":     outputs,
        "stats":            stats,
    }
    try:
        _coll.insert_one(record)
        print(f"📜  Lineage record written (run_id={record['_run_id'][:8]})")
    except Exception as e:
        print(f"⚠️  Failed to write lineage record: {e}")
