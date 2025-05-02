# coursework_two/modules/minio_client.py

from pathlib import Path
from minio import Minio
from minio.error import S3Error
from modules.extract.config_loader import (
    MINIO_ENDPOINT,
    MINIO_ACCESS_KEY,
    MINIO_SECRET_KEY,
    MINIO_BUCKET,
    MINIO_SECURE
)

# 初始化 MinIO 客户端
_client = Minio(
    MINIO_ENDPOINT.replace("http://", "").replace("https://", ""),
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=MINIO_SECURE,
)

def download_pdf(object_name: str, dest: Path) -> Path:
    """
    从 MinIO 下载 PDF 到本地 dest。
    object_name: bucket 中的 key，例如 "reports/2024_report.pdf"
    dest:         本地保存路径
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        _client.fget_object(MINIO_BUCKET, object_name, str(dest))
        print(f"✅ Downloaded {object_name} to {dest}")
        return dest
    except S3Error as e:
        raise RuntimeError(f"Failed to download {object_name} from MinIO: {e}")
