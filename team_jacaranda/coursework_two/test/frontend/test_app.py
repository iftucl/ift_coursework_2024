import pytest
import re
import os

# 结构检查：检查 App.js 代码结构是否合理
def test_app_structure():
    # 获取当前测试文件所在目录
    current_dir = os.path.dirname(__file__)
    App_js_path = os.path.join(current_dir, "../../modules/frontend/src/App.js")

    # 读取 App.js 文件内容
    with open(App_js_path, "r", encoding="utf-8") as f:
        app_content = f.read()

    # 基本检查
    assert "useState" in app_content, "App.js 应该使用 useState hook"
    assert "return (" in app_content, "App.js 应该有一个返回的 JSX"
    assert "<input" in app_content, "App.js 应该包含一个 input 元素"
    assert "<button" in app_content, "App.js 应该包含一个 button 元素"

# 功能检查（这里只能静态检查代码）
def test_app_contains_add_functionality():
    with open("modules/frontend/src/App.js", "r", encoding="utf-8") as f:
        app_content = f.read()

    # 检查是否有 onClick 事件绑定
    assert "onClick" in app_content, "App.js 应该有按钮点击处理逻辑"

    # 检查是否存在以 set 开头的状态更新函数调用
    set_call_pattern = re.compile(r'set\w+\s*\(')
    assert re.search(set_call_pattern, app_content), "App.js 应该有状态更新逻辑（调用 setXXX 函数）"
