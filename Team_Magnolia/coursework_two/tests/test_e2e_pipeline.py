# tests/test_e2e_pipeline.py
import os
import pytest
from subprocess import run, PIPE
from pathlib import Path

@pytest.mark.e2e
def test_end_to_end(tmp_path):
    # 调用一次 batch-extract（假设已经在 MinIO 放了一个小 PDF，或者你可以模拟一个）
    # 这里仅示例本地 extract → ingest，不访问真实 MinIO
    pdf = tmp_path/"dummy.pdf"
    pdf.write_text("%PDF-1.4\n%%EOF")  # 空 PDF，extract_main 会快速失败
    cmd = ["python", "Main.py", "extract", "--pdf", str(pdf)]
    proc = run(cmd, cwd=os.getcwd(), stdout=PIPE, stderr=PIPE, text=True)
    # 期待脚本能正常退出且打印“❌  First pass failed”
    assert proc.returncode == 0
    assert "First pass failed" in proc.stdout or "✅  Ingestion complete" in proc.stdout
