import requests
import fitz
import re

def download_pdf(pdf_url, local_path):
    """
    Download a PDF from the specified URL and save it to a local file path.

    Args:
        pdf_url (str): The URL of the PDF file to download.
        local_path (str): The path to save the downloaded PDF file locally.

    Raises:
        Exception: If the PDF could not be downloaded successfully.
    """
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(pdf_url, headers=headers, timeout=10)
    if response.status_code == 200:
        with open(local_path, "wb") as f:
            f.write(response.content)
    else:
        raise Exception(f"Failed to download PDF: {pdf_url}")

def extract_text_from_pdf(pdf_path):
    """
    Extract text content from all pages of a PDF file.

    Args:
        pdf_path (str): Path to the local PDF file to read.

    Returns:
        tuple: A tuple containing:
            - full_text (str): Concatenated text of all pages.
            - pages_text (list): A list where each element is the text of a single page.
    """
    doc = fitz.open(pdf_path)
    full_text = ""
    pages_text = []

    for page in doc:
        page_text = page.get_text()
        full_text += page_text
        pages_text.append(page_text)

    return full_text, pages_text

def clean_response(response):
    """
    Clean the response text by removing Markdown-style code block markers (```json, ```).

    Args:
        response (str): The raw response text to clean.

    Returns:
        str: The cleaned response text.
    """
    cleaned = re.sub(r"```json|```", "", response).strip()
    return cleaned