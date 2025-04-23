# test_llm_analyse.py
from modules.data_storage import llm_analyse
import json

def test_prompt_formatting():
    prompt = llm_analyse.build_prompt("Energy Intensity", "desc", False, [{"page": 1, "text": "This is test."}], 2022)
    assert "Energy Intensity" in prompt and "desc" in prompt

