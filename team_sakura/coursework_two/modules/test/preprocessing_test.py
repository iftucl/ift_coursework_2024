# tests/test_preprocess.py
import pytest
from coursework_two.modules.utils.preprocessing import preprocess_text

@pytest.mark.parametrize("input_text, expected", [
    # Remove extra newlines
    ("Line1\n\n\nLine2", "Line1\nLine2"),

    # Remove multiple spaces
    ("Line1    Line2", "Line1 Line2"),

    # Merge broken Scope + Emissions lines
    ("Scope 1 \n Emissions", "Scope 1 Emissions"),
    ("Scope 2\n Emissions", "Scope 2 Emissions"),

    # Merge broken indicator/value lines
    ("Scope 1 Emissions\n32400 metric tons\n", "Scope 1 Emissions: 32400 metric tons\n"),
    ("Scope 3 Emissions\n12,400 kg\n", "Scope 3 Emissions: 12,400 kg\n"),
])
def test_preprocess_text(input_text, expected):
    assert preprocess_text(input_text) == expected