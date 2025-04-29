import pytest
from unittest.mock import patch
import os

def test_index_imports_and_mounts():
    # 获取当前测试文件所在目录
    current_dir = os.path.dirname(__file__)
    index_js_path = os.path.join(current_dir, "../../modules/frontend/src/index.js")

    # 读取 index.js 文件内容
    with open(index_js_path, "r", encoding="utf-8") as f:
        index_js_content = f.read()

    # 确保 index.js 中有正确的导入和挂载语句
    # 检查是否有 "import App from"（检查是否导入了 App 组件）
    assert "import App from" in index_js_content
    # 检查是否有 "createRoot"（检查是否调用了 ReactDOM.createRoot）
    assert "createRoot" in index_js_content
    # 检查是否有 "root.render"（检查是否调用了 root.render 渲染 App 组件）
    assert "root.render" in index_js_content

'''
# python中无法直接mock JS模块react-dom
# 在Pytest环境下读取.js，但它不是Python模块
# Python无法真正“执行”JS文件逻辑，除非用Node.js测试框架或JS bridge
# 故需要删除此函数
def test_create_root_and_render():
    # 使用 unittest.mock.patch 来模拟 createRoot 和 render 函数
    with patch("react_dom.createRoot") as mock_create_root:
        mock_root = mock_create_root.return_value
        with patch.object(mock_root, "render") as mock_render:
            # 调用 index.js 中的渲染逻辑（假设 index.js 里有直接执行挂载的代码）
            # 这里只是模拟模块加载和渲染调用，而不是实际执行
            import src.index  # 这行会触发 index.js 中的挂载逻辑
            
            # 验证 createRoot 和 render 是否被正确调用
            mock_create_root.assert_called_once_with(mock_root)
            mock_render.assert_called_once()
'''