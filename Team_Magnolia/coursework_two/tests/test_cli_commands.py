import json
import argparse
from pathlib import Path

import pytest

from Main import convert_command
from modules.extract.config_loader import FINAL_JSON, OUTPUT_CSV

def test_convert_command(tmp_path, monkeypatch):
    # 1) 准备一个简单的 final_standardized.json
    data = {
        "ThemeOne": [
            {
                "indicator_name": "TestInd",
                "years": [2023],
                "values_numeric": [123],
                "values_text": None,
                "unit": "unit",
                "page_number": [1],
                "source": "src"
            }
        ]
    }
    in_json = tmp_path / FINAL_JSON
    in_json.write_text(json.dumps(data, ensure_ascii=False, indent=2))

    # 2) 指定输出 CSV 路径
    out_csv = tmp_path / OUTPUT_CSV

    # 3) 构造 args 并调用 convert_command
    args = argparse.Namespace(json_file=str(in_json), csv_file=str(out_csv))
    convert_command(args)

    # 4) 验证 CSV 文件已创建且内容包含指标和数值
    assert out_csv.exists(), "CSV file was not created"
    content = out_csv.read_text(encoding="utf-8")
    assert "TestInd" in content
    assert "123" in content
