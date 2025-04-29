import pytest
import types
import os
import subprocess
import builtins
import logging
from modules.data_storage import main

def test_read_completed_modules(tmp_path, monkeypatch):
    # 情况1: 文件不存在
    fake_path = tmp_path / "no_such_file.txt"
    monkeypatch.setattr(main, "completed_file_path", str(fake_path))
    result = main.read_completed_modules()
    assert result == set()  # 不存在应返回空集合
    # 情况2: 文件存在并有内容
    file_path = tmp_path / "completed_modules.txt"
    file_path.write_text("moduleA.py\nmoduleB.py\n")
    monkeypatch.setattr(main, "completed_file_path", str(file_path))
    result = main.read_completed_modules()
    # 返回集合应包含文件中的模块名
    assert result == {"moduleA.py", "moduleB.py"}

def test_write_completed_module(tmp_path, monkeypatch):
    file_path = tmp_path / "completed.txt"
    monkeypatch.setattr(main, "completed_file_path", str(file_path))
    # 确保文件初始不存在或为空
    if file_path.exists():
        file_path.unlink()
    main.write_completed_module("mod1.py")
    main.write_completed_module("mod2.py")
    # 读取文件验证内容
    content = file_path.read_text().splitlines()
    assert "mod1.py" in content and "mod2.py" in content
    # 顺序追加，每个模块一行
    assert content[-2:] == ["mod1.py", "mod2.py"]

def test_run_command_success_and_failure(monkeypatch):
    # 模拟成功执行，不抛异常
    called = {"cmd": None}
    monkeypatch.setattr(subprocess, "run", lambda cmd, check, shell: called.update({"cmd": cmd}))
    # 调用 run_command，验证不会退出
    main.run_command("echo 'hi'")
    assert called["cmd"] == "echo 'hi'"
    # 模拟失败执行，subprocess.run 抛出 CalledProcessError
    def fake_run(cmd, check, shell):
        raise subprocess.CalledProcessError(1, cmd, "Error")
    monkeypatch.setattr(subprocess, "run", fake_run)
    # 捕获 sys.exit 调用
    with pytest.raises(SystemExit) as excinfo:
        main.run_command("false")
    assert excinfo.value.code == 1

def test_main_skip_and_execute(monkeypatch):
    """测试 main() 对已完成模块的跳过和未完成模块的执行顺序"""
    # 模拟部分模块已完成
    completed = {"create_table.py", "llm_analyse.py"}
    monkeypatch.setattr(main, "read_completed_modules", lambda: completed)
    # 记录执行的命令和写入的模块
    executed_cmds = []
    written_modules = []
    monkeypatch.setattr(main, "run_command", lambda cmd: executed_cmds.append(cmd))
    monkeypatch.setattr(main, "write_completed_module", lambda module: written_modules.append(module))
    # 替换 tqdm.tqdm 为 dummy，避免实际显示进度
    class DummyPbar:
        def __enter__(self): return self
        def __exit__(self, exc_type, exc, tb): return False
        def update(self, n): pass
    monkeypatch.setattr(main, "tqdm", lambda total, desc, ncols: DummyPbar())
    # 执行 main()
    main.main()
    # 验证第一个命令是安装依赖
    assert executed_cmds[0] == "poetry install"
    # 生成应执行的模块列表（跳过completed的）
    expected_order = [
        "poetry run python modules/data_storage/paragraph_extraction.py",
        "poetry run python modules/data_storage/retry_failed_reports.py",
        "poetry run python modules/data_storage/llm_standardize.py",
        "poetry run python modules/data_storage/data_export.py"
    ]
    # executed_cmds 包含安装命令+上述模块命令
    assert executed_cmds[1:] == expected_order
    # 确认跳过的模块未出现在执行列表
    for mod in completed:
        mod_cmd = f"poetry run python modules/data_storage/{mod}"
        assert mod_cmd not in executed_cmds
    # write_completed_module 应对未跳过模块调用
    written_modules_set = set(written_modules)
    expected_written = {"paragraph_extraction.py", "retry_failed_reports.py", "llm_standardize.py", "data_export.py"}
    assert expected_written.issubset(written_modules_set)

def test_main_pipeline_failure(monkeypatch):
    """测试 main() 在某个模块失败时的退出"""
    monkeypatch.setattr(main, "read_completed_modules", lambda: set())
    # 计数以确定退出发生时的位置
    call_count = {"count": 0}
    def fake_run_command(cmd):
        call_count["count"] += 1
        # 模拟在第二个模块失败
        if "paragraph_extraction.py" in cmd:
            raise SystemExit(1)
    monkeypatch.setattr(main, "run_command", fake_run_command)
    monkeypatch.setattr(main, "write_completed_module", lambda module: None)
    monkeypatch.setattr(main, "tqdm", lambda total, desc, ncols: types.SimpleNamespace(__enter__=lambda self: self, __exit__=lambda self, exc_type, exc, tb: False, update=lambda n: None))
    # 捕获 SystemExit
    with pytest.raises(SystemExit) as excinfo:
        main.main()
    assert excinfo.value.code == 1
    # 验证在失败时退出，没有执行后续模块
    # call_count == 2 表示执行了安装和第一个模块，然后在第二个模块退出
    assert call_count["count"] == 2
