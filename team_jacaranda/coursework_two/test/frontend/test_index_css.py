import pytest
import os

def test_custom_checkbox_class_exists():
    # 获取当前测试文件所在目录
    current_dir = os.path.dirname(__file__)
    index_css_path = os.path.join(current_dir, "../../modules/frontend/src/index.css")

    # 读取 index.css 文件内容
    with open(index_css_path, "r", encoding="utf-8") as f:
        css_content = f.read()
    
    assert ".custom-checkbox" in css_content
    assert ".custom-checkbox:checked" in css_content
    assert ".loading-spinner" in css_content
    assert ".error-message" in css_content
    #更完整地验证Tailwind是否接入
    assert "@tailwind base" in css_content
    assert "@tailwind components" in css_content
    assert "@tailwind utilities" in css_content
