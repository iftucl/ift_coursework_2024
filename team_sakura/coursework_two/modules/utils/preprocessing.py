import re

def preprocess_text(raw_text: str) -> str:
    """
    Preprocess raw extracted text from PDF for cleaner and more structured format.

    This function performs several text cleaning and formatting tasks:
    - Removes excessive newlines.
    - Removes multiple spaces.
    - Merges broken lines in indicator names (e.g., "Scope 1 \n Emissions" → "Scope 1 Emissions").
    - Merges broken lines between indicator names and values (e.g., "Scope 1 Emissions\n32400 metric tons" → "Scope 1 Emissions: 32400 metric tons").

    Args:
        raw_text (str): The raw extracted text from a PDF document.

    Returns:
        str: The cleaned and preprocessed text.
    """
    # Remove extra newlines
    text = re.sub(r'\n+', '\n', raw_text)

    # Remove multiple spaces
    text = re.sub(r'[ ]{2,}', ' ', text)

    # Merge broken lines for indicator names like "Scope 1 \n Emissions"
    text = re.sub(r'(Scope\s+\d)\s*\n\s*(Emissions)', r'\1 \2', text, flags=re.IGNORECASE)

    # Merge broken lines between indicator and its value, like "Scope 1 Emissions\n32400 metric tons"
    text = re.sub(r'(Scope\s+\d\s+Emissions)\s*\n\s*([\d,\.]+.*?)\n', r'\1: \2\n', text, flags=re.IGNORECASE)

    return text
