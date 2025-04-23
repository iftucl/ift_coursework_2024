# test_paragraph_extraction.py
from modules.data_storage import paragraph_extraction

def test_find_matching_paragraphs():
    paras = [(1, "This mentions renewable energy and solar power.")]
    keywords = ["renewable", "solar"]
    matched = paragraph_extraction.find_matching_paragraphs(paras, keywords)
    assert len(matched) == 1