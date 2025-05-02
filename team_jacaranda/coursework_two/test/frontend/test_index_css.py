"""
Module: test_custom_checkbox_class_exists

This module contains a test function that checks if the necessary CSS classes related to 
the custom checkbox, loading spinner, and error message elements are defined within 
the `index.css` file of the frontend project. It also verifies that Tailwind CSS has 
been properly integrated into the project by checking for the presence of its directives.

Test case:
- Verifies the existence of specific CSS classes (`.custom-checkbox`, `.custom-checkbox:checked`, `.loading-spinner`, and `.error-message`).
- Verifies that Tailwind CSS directives (`@tailwind base`, `@tailwind components`, and `@tailwind utilities`) are included in the `index.css` file.
"""

import pytest
import os

def test_custom_checkbox_class_exists():
    """
    Test the existence of essential CSS classes and Tailwind integration in the `index.css` file.

    This test function reads the contents of the `index.css` file, which is part of the frontend
    project, and checks for the presence of the following:
    - `.custom-checkbox`: A class that should define custom checkbox styles.
    - `.custom-checkbox:checked`: A pseudo-class for checked custom checkboxes.
    - `.loading-spinner`: A class to define the loading spinner styles.
    - `.error-message`: A class to define the error message styles.
    - Tailwind CSS directives: Verifies that the `@tailwind` directives for `base`, `components`, 
    and `utilities` are present to ensure Tailwind CSS is integrated into the project.

    :raises AssertionError: If any of the CSS classes or Tailwind CSS directives are missing.
    """
    # Get the directory where the test file is located
    current_dir = os.path.dirname(__file__)
    index_css_path = os.path.join(current_dir, "../../modules/frontend/src/index.css")

    # Read the content of the index.css file
    with open(index_css_path, "r", encoding="utf-8") as f:
        css_content = f.read()
    
    # Perform assertions to check for the required classes and Tailwind CSS directives
    assert ".custom-checkbox" in css_content, "The .custom-checkbox class is missing in index.css."
    assert ".custom-checkbox:checked" in css_content, "The .custom-checkbox:checked pseudo-class is missing in index.css."
    assert ".loading-spinner" in css_content, "The .loading-spinner class is missing in index.css."
    assert ".error-message" in css_content, "The .error-message class is missing in index.css."
    assert "@tailwind base" in css_content, "The @tailwind base directive is missing in index.css."
    assert "@tailwind components" in css_content, "The @tailwind components directive is missing in index.css."
    assert "@tailwind utilities" in css_content, "The @tailwind utilities directive is missing in index.css."
