"""
MinIO helper
────────────────────────────────────────────────────────────────
• download_pdf(object_name, dest)     单文件下载
• list_objects(prefix=None)           批量列举
"""
from pathlib import Path
from typing import List, Optional, Set   # ← 新增 Set

from minio import Minio
from minio.error import S3Error

from modules.extract.config_loader import (
    MINIO_ENDPOINT,
    MINIO_ACCESS_KEY,
    MINIO_SECRET_KEY,
    MINIO_BUCKET,
    MINIO_SECURE,
)

# ──────────────────────────────────────────────────────────────
# 初始化 MinIO 客户端
# ──────────────────────────────────────────────────────────────
_client = Minio(
    MINIO_ENDPOINT.replace("http://", "").replace("https://", ""),
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=MINIO_SECURE,
)

# ──────────────────────────────────────────────────────────────
# 1) 单文件下载（原逻辑不变）
# ──────────────────────────────────────────────────────────────
def download_pdf(object_name: str, dest: Path) -> Path:
    """
    从 MinIO 下载 PDF 到本地 dest。
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        _client.fget_object(MINIO_BUCKET, object_name, str(dest))
        print(f"✅ Downloaded {object_name} to {dest}")
        return dest
    except S3Error as e:
        raise RuntimeError(f"Failed to download {object_name} from MinIO: {e}")

# ──────────────────────────────────────────────────────────────
# 2) 批量列举（改进：递归 + 去重 + 只取 PDF）
# ──────────────────────────────────────────────────────────────
def list_objects(prefix: Optional[str] = None) -> List[str]:
    """
    列举 bucket 中的 PDF 对象 key（递归子目录，自动去重）。

    Parameters
    ----------
    prefix : str | None
        仅返回以该前缀开头的对象；None → 列举整个桶。

    Returns
    -------
    list[str]
        按字母序排序、不重复的 PDF key 列表
    """
    try:
        it = _client.list_objects(
            bucket_name=MINIO_BUCKET,
            prefix=prefix,
            recursive=True,           # 递归列举
        )

        seen: Set[str] = set()
        keys: List[str] = []
        for obj in it:
            key = obj.object_name.strip()
            if not key.lower().endswith(".pdf"):
                continue
            if key in seen:           # 处理 MinIO 可能返回的重复项
                continue
            seen.add(key)
            keys.append(key)

        return sorted(keys, key=str.lower)
    except S3Error as e:
        print(f"[ERROR] MinIO list_objects failed: {e}")
        return []
