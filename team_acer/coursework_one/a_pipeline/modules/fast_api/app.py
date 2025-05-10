from fastapi import FastAPI, HTTPException
from typing import List, Optional
import psycopg2
import boto3
from botocore.exceptions import ClientError
from modules.minio_writer.store_minio import ensure_minio_bucket
from modules.extracting_csr_reports.fetch_csr_reports import fetch_csr_reports
import os

# =============================
#        CONFIGURATION
# =============================

def _init_(self, name, age):
    self.name = name
    self.age = age

DB_HOST = "localhost"
DB_PORT = "5439"
DB_NAME = "fift"
DB_USER = "postgres"
DB_PASSWORD = "postgres"

MINIO_ENDPOINT = "http://localhost:9000"
MINIO_ACCESS_KEY = "ift_bigdata"
MINIO_SECRET_KEY = "minio_password"
BUCKET_NAME = "csr-reports"

minio_client = boto3.client(
    "s3",
    endpoint_url=MINIO_ENDPOINT,
    aws_access_key_id=MINIO_ACCESS_KEY,
    aws_secret_access_key=MINIO_SECRET_KEY,
)

ensure_minio_bucket()  # ✅ Ensures MinIO bucket exists before API starts

# =============================
#        DATABASE CONNECTION
# =============================

def get_db_connection():
    """Connects to PostgreSQL database using a context manager."""
    try:
        return psycopg2.connect(
            host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD
        )
    except psycopg2.OperationalError as e:
        raise HTTPException(status_code=500, detail=f"Database connection error: {e}")

# =============================
#        FASTAPI APP
# =============================

app = FastAPI(
    title="CSR Report API",
    description="API to retrieve metadata and check availability of CSR reports",
    version="1.0.0",
)

# =============================
#       API ENDPOINTS
# =============================

@app.get("/")
def home():
    return {"message": "Welcome to the CSR Report API!"}

@app.get("/run-extraction/")
def run_extraction():
    """
    Manually trigger CSR report extraction.
    """
    fetch_csr_reports()
    return {"message": "CSR Report extraction started"}

@app.get("/reports/")
def get_reports(
    symbol: Optional[str] = None,
    security: Optional[str] = None,
    year: Optional[int] = None,
):
    """
    Retrieve CSR reports metadata based on company symbol, name, or year.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = "SELECT * FROM csr_metadata WHERE 1=1"
        params = []

        if symbol:
            query += " AND symbol = %s"
            params.append(symbol)
        if security:
            query += " AND security ILIKE %s"
            params.append(f"%{security}%")
        if year:
            query += " AND year = %s"
            params.append(year)

        cursor.execute(query, tuple(params))
        results = cursor.fetchall()
        cursor.close()
        conn.close()

        if not results:
            raise HTTPException(status_code=404, detail="No reports found.")

        return [
            {
                "symbol": row[0],
                "security": row[1],
                "year": row[2],
                "region": row[3],
                "country": row[4],
                "sector": row[5],
                "industry": row[6],
                "minio_url": row[7],
            }
            for row in results
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/reports/{region}/{country}/{sector}/{industry}/{symbol}/{year}/exists")
def check_report_exists(region: str, country: str, sector: str, industry: str, symbol: str, year: int):
    """
    Check if a CSR report exists in MinIO storage using the correct folder structure.
    """
    minio_key = f"{region}/{country}/{sector}/{industry}/{symbol}/{year}/{symbol}_CSR_{year}.pdf"

    try:
        minio_client.head_object(Bucket=BUCKET_NAME, Key=minio_key)
        return {"exists": True, "minio_url": f"{MINIO_ENDPOINT}/{BUCKET_NAME}/{minio_key}"}
    except ClientError:
        return {"exists": False}


# =============================
#        RUN FASTAPI
# =============================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080, reload=True)