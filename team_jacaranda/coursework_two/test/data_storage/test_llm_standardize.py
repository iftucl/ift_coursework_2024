# test_llm_standardize.py
from modules.data_storage import llm_standardize

def test_conversion_prompt():
    prompt = llm_standardize.build_conversion_prompt("GHG", "desc", "100", "%", "%")
    assert "100" in prompt and "%" in prompt
