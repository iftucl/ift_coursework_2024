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
    # 1. 建立客户端
    minio_client = Minio(
        Config.MINIO_ENDPOINT,
        access_key=Config.MINIO_ACCESS_KEY,
        secret_key=Config.MINIO_SECRET_KEY,
        secure=False
    )
    pg = PostgresManager(
        host="localhost",         # 根据你的实际改
        port="5439",              # 改成你 Postgres 端口
        user="postgres",
        password="postgres",
        dbname="postgres"
    )
    # 2. 清空旧记录
    pg.cur.execute("""
    SELECT EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name = 'pdf_records'
    );
    """)
    exists = pg.cur.fetchone()[0]

    if exists:
        print("✅ 表 pdf_records 存在，可以安全 TRUNCATE")
    else:
        print("❌ 表 pdf_records 不存在，需要先创建")

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
    


    # 3. 遍历 MinIO 桶
    success_count=0
    for obj in minio_client.list_objects(Config.MINIO_BUCKET, recursive=True):
        filename = obj.object_name  # e.g. "Apple Inc_2022.pdf"
        print(f"Dealing with: {filename}")
        # 4. 从文件名拆 company & year
        try:
            base, ext = filename.rsplit('.', 1)
            company, year_str = base.rsplit('_', 1)
            year = int(year_str)
        except Exception:
            print(f"[Sync] Skip unparsable filename: {filename}")
            continue
        

        # 5. 取回对象计算哈希
        data = minio_client.get_object(Config.MINIO_BUCKET, filename)
        content = data.read()
        content_hash = hashlib.md5(content).hexdigest()

        # 6. 构造 record 并 UPSERT
        record = {
            "company": company,
            "url": "",               # MinIO 对象没有原始 URL，这里留空
            "year": year,
            "file_hash": content_hash,
            "filename": filename
        }
        pg.insert_pdf_record(record)
        print(f"[Sync] Upserted {filename}")
        success_count += 1

    # 7. 收尾
    pg.close()
    print("[Sync] Done.")
    print(f"[Sync] ✅ 同步完成，共处理 {success_count} 个文件。")

if __name__ == "__main__":
    print("开始同步 MinIO → Postgres")
    sync_minio_to_postgres()

