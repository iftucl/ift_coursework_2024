# sync_minio_to_postgres.py

import time
import hashlib
import datetime
from minio import Minio
import sys
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../../../.."))
sys.path.append(project_root)
from coursework_one.a_pipeline.modules.url_parser.database import PostgresManager
from coursework_one.a_pipeline.modules.db_loader.crawler import Config

def sync_minio_to_postgres():
    # 1. Create a client
    minio_client = Minio(
        Config.MINIO_ENDPOINT,
        access_key=Config.MINIO_ACCESS_KEY,
        secret_key=Config.MINIO_SECRET_KEY,
        secure=False
    )
    pg = PostgresManager(
        host="localhost",         
        port="5439",              
        user="postgres",
        password="postgres",
        dbname="postgres"
    )
  # 2. Clear old records
    pg.cur.execute("""
    SELECT EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name = 'pdf_records'
    );
    """)
    exists = pg.cur.fetchone()[0]

    if exists:
        print("✅ Table pdf_records exists and can be TRUNCATE safely")
    else:
        print("❌ Table pdf_records does not exist and needs to be created first")

    pg.cur.execute(f"""
    SELECT COUNT(*)
    FROM pg_locks l
    JOIN pg_class t ON l.relation = t.oid
    WHERE t.relname = 'pdf_records';
    """)
    count = pg.cur.fetchone()[0]
    if count > 0:
        print(f"⚠️ Warning: Table pdf_records is locked by {count} transactions.")
    else:
        print(f"✅ Table pdf_records is not locked.")
    

    pg.cur.execute("TRUNCATE TABLE pdf_records;")
    pg.conn.commit()
    print("[Sync] Cleared pdf_records table.")
    print(f"[Check] Listing objects in bucket: {Config.MINIO_BUCKET}")
    objects = list(minio_client.list_objects(Config.MINIO_BUCKET, recursive=True))
    print(f"[Check] Found {len(objects)} objects.")
    


    # 3. Traverse MinIO buckets
    success_count=0
    for obj in minio_client.list_objects(Config.MINIO_BUCKET, recursive=True):
        filename = obj.object_name  # e.g. "Apple Inc_2022.pdf"
        print(f"Dealing with: {filename}")
        # 4. Remove company & year from the file name
        try:
            base, ext = filename.rsplit('.', 1)
            company, year_str = base.rsplit('_', 1)
            year = int(year_str)
        except Exception:
            print(f"[Sync] Skip unparsable filename: {filename}")
            continue
        

       # 5. Retrieve the object and calculate the hash
        data = minio_client.get_object(Config.MINIO_BUCKET, filename)
        content = data.read()
        content_hash = hashlib.md5(content).hexdigest()

        # 6. Construct record and UPSERT
        record = {
            "company": company,
            "url": "",               # MinIO objects do not have a raw URL, leave this blank
            "year": year,
            "file_hash": content_hash,
            "filename": filename
        }
        pg.insert_pdf_record(record)
        print(f"[Sync] Upserted {filename}")
        success_count += 1

    # 7. Finishing
    pg.close()
    print("[Sync] Done.")
    print(f"[Sync] ✅ Sync completed, processing {success_count} files in total.")

if __name__ == "__main__":
    print("Start syncing MinIO → Postgres")
    sync_minio_to_postgres()

