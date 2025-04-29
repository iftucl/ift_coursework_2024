import fitz               # PyMuPDF
from minio import Minio
from minio.error import S3Error
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

# —— 1. 日志配置 —— 
logging.basicConfig(
    filename='process_reports.log',
    level=logging.INFO,
    format='%(asctime)s %(levelname)s:%(message)s'
)

# —— 2. MinIO 客户端 —— 
client = Minio(
    "localhost:9000",         # 或者 "127.0.0.1:9000"
    access_key="ift_bigdata",
    secret_key="minio_password",
    secure=False
)

input_bucket = "report1"
output_bucket = "report"

# —— 3. 单个文件处理函数 —— 
def process_pdf(obj_name: str):
    # 生成对应的 txt 名称
    txt_name = obj_name.rsplit(".", 1)[0] + ".txt"
    
    # —— 跳过已存在的 txt —— 
    try:
        # 如果能 stat 成功，说明已经转换过了
        client.stat_object(output_bucket, txt_name)
        logging.info(f"⏭ 跳过已存在：{txt_name}")
        return
    except S3Error:
        # 不存在则继续
        pass

    try:
        # 下载 PDF
        resp = client.get_object(input_bucket, obj_name)
        pdf_bytes = resp.read()
        resp.close()
        resp.release_conn()

        # 提取文本
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = []
        for p in range(doc.page_count):
            text.append(doc.load_page(p).get_text())
        doc.close()
        txt_data = "\n".join(text).encode("utf-8")

        # 上传 TXT
        client.put_object(
            bucket_name=output_bucket,
            object_name=txt_name,
            data=BytesIO(txt_data),
            length=len(txt_data),
            content_type="text/plain; charset=utf-8"
        )

        logging.info(f"✔ {obj_name} -> {txt_name}")
    except Exception as e:
        logging.error(f"✘ {obj_name} 处理失败：{e}")

# —— 4. 并发执行 —— 
if __name__ == "__main__":
    # 1) 列出所有 PDF 对象
    all_pdfs = [
        obj.object_name
        for obj in client.list_objects(input_bucket, recursive=True)
        if obj.object_name.lower().endswith(".pdf")
    ]

    # 2) 读取已存在的 txt
    existing_txts = {
        obj.object_name
        for obj in client.list_objects(output_bucket, recursive=True)
        if obj.object_name.lower().endswith(".txt")
    }

    # 3) 过滤：只留还没生成 txt 的
    pending_pdfs = [
        pdf for pdf in all_pdfs
        if (pdf.rsplit(".", 1)[0] + ".txt") not in existing_txts
    ]

    total = len(pending_pdfs)
    logging.info(f"发现 {len(all_pdfs)} 个 PDF，{len(existing_txts)} 个已转换，剩余 {total} 个待处理。")

    # 4) 使用线程池并发处理
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(process_pdf, name): name for name in pending_pdfs}
        for i, fut in enumerate(as_completed(futures), 1):
            name = futures[fut]
            print(f"[{i}/{total}] {name}")
