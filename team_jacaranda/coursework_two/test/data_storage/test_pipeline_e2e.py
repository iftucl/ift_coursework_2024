# test_pipeline_e2e.py
from subprocess import run

def test_pipeline_e2e():
    result = run(["poetry", "run", "python", "modules/data_storage/main.py"])
    assert result.returncode == 0
