import fitz               # PyMuPDF
from minio import Minio
from minio.error import S3Error
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

# —— 1.Log Configuration —— 
logging.basicConfig(
    filename='process_reports.log',
    level=logging.INFO,
    format='%(asctime)s %(levelname)s:%(message)s'
)

# —— 2. MinIO Client —— 
client = Minio(
    "localhost:9000",        # or "127.0.0.1:9000"
    access_key="ift_bigdata",
    secret_key="minio_password",
    secure=False
)

input_bucket = "report1"
output_bucket = "report"

# —— 3. Single file processing function —— 
def process_pdf(obj_name: str):
    # Generate the corresponding txt name
    txt_name = obj_name.rsplit(".", 1)[0] + ".txt"
    
    # —— Skip existing txt —— 
    try:
        # If stat succeeds, it means it has been converted.
        client.stat_object(output_bucket, txt_name)
        logging.info(f"⏭ Skip already exists：{txt_name}")
        return
    except S3Error:
        # If not present, continue
        pass

    try:
        # Download PDF
        resp = client.get_object(input_bucket, obj_name)
        pdf_bytes = resp.read()
        resp.close()
        resp.release_conn()

        # Extract text
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = []
        for p in range(doc.page_count):
            text.append(doc.load_page(p).get_text())
        doc.close()
        txt_data = "\n".join(text).encode("utf-8")

        # Upload TXT
        client.put_object(
            bucket_name=output_bucket,
            object_name=txt_name,
            data=BytesIO(txt_data),
            length=len(txt_data),
            content_type="text/plain; charset=utf-8"
        )

        logging.info(f"✔ {obj_name} -> {txt_name}")
    except Exception as e:
        logging.error(f"✘ {obj_name} Handling failure：{e}")

# —— 4. Concurrent Execution —— 
if __name__ == "__main__":
    # 1) List all PDF objects
    all_pdfs = [
        obj.object_name
        for obj in client.list_objects(input_bucket, recursive=True)
        if obj.object_name.lower().endswith(".pdf")
    ]

    # 2) Read existing txt
    existing_txts = {
        obj.object_name
        for obj in client.list_objects(output_bucket, recursive=True)
        if obj.object_name.lower().endswith(".txt")
    }

    # 3) Filter: Only keep those that have not yet generated txt
    pending_pdfs = [
        pdf for pdf in all_pdfs
        if (pdf.rsplit(".", 1)[0] + ".txt") not in existing_txts
    ]

    total = len(pending_pdfs)
    logging.info(f"{len(all_pdfs)} PDFs found, {len(existing_txts)} converted, {total} remaining to be processed.")

    # 4) Using thread pool for concurrent processing
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(process_pdf, name): name for name in pending_pdfs}
        for i, fut in enumerate(as_completed(futures), 1):
            name = futures[fut]
            print(f"[{i}/{total}] {name}")
