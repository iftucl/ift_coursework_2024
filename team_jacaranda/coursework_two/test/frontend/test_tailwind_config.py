import importlib.util
import pytest
import os

def test_tailwind_config_contains_expected_keys():
    # 获取当前测试文件所在目录
    current_dir = os.path.dirname(__file__)
    tailwind_config_js_path = os.path.join(current_dir, "../../modules/frontend/tailwind.config.js")

    # 读取 tailwind.config.js 文件内容
    with open(tailwind_config_js_path, "r", encoding="utf-8") as f:
        config_content = f.read()

    assert "module.exports" in config_content
    assert "theme:" in config_content
    assert "extend:" in config_content
    assert "'#1a8c70'" in config_content  # 检查自定义颜色值
    assert "pulse" in config_content  # 检查动画名


'''
def load_tailwind_config():
    # 加载 src/tailwind.config.js 文件
    spec = importlib.util.spec_from_file_location("tailwind_config", "./modules/frontend/tailwind.config.js")
    config = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config)
    return config

def test_teal_color_500():
    config = load_tailwind_config()
    assert config.theme['extend']['colors']['teal']['500'] == '#1a8c70'

def test_animation_pulse_defined():
    config = load_tailwind_config()
    assert 'pulse' in config.theme['extend']['animation']
'''
