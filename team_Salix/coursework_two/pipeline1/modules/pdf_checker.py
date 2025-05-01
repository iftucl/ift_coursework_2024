import csv
import glob
import os
import subprocess

from PyPDF2 import PdfReader, PdfWriter
from tqdm import tqdm


def try_decrypt_pdf(pdf_path):
    """Try to decrypt PDF using pdfcrack."""
    try:
        # First try with empty password
        reader = PdfReader(pdf_path)
        if reader.is_encrypted:
            if reader.decrypt(""):
                return True, ""

        # If empty password doesn't work, try pdfcrack
        output_path = os.path.join(os.path.dirname(pdf_path), "decrypted_" + os.path.basename(pdf_path))

        # Try pdfcrack with common wordlist
        result = subprocess.run(
            ["pdfcrack", "-f", pdf_path, "-w", "/usr/share/wordlists/rockyou.txt"],
            capture_output=True,
            text=True,
        )

        if "Password found" in result.stdout:
            # Extract password from output
            password = result.stdout.split("Password found: ")[1].strip()
            return True, password
        return False, None
    except Exception as e:
        print(f"Error in decryption attempt: {str(e)}")
        return False, None


def check_pdf_encryption(pdf_path):
    """Check if a PDF file is encrypted and can be read."""
    try:
        reader = PdfReader(pdf_path)
        # Check if PDF is encrypted
        if reader.is_encrypted:
            # Try to decrypt
            decrypted, password = try_decrypt_pdf(pdf_path)
            if decrypted:
                return (
                    True,
                    f"PDF was encrypted but decrypted successfully with password: {password}",
                )
            else:
                return False, "PDF is encrypted and could not be decrypted"

        # Try to read the first page to verify it's readable
        if len(reader.pages) > 0:
            _ = reader.pages[0].extract_text()
            return True, "PDF is readable"
        else:
            return False, "PDF has no pages"

    except Exception as e:
        return False, f"Error reading PDF: {str(e)}"


def save_decrypted_pdf(pdf_path, password, output_path):
    """Save a decrypted version of the PDF."""
    try:
        reader = PdfReader(pdf_path)
        if reader.decrypt(password):
            writer = PdfWriter()
            for page in reader.pages:
                writer.add_page(page)

            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "wb") as output_file:
                writer.write(output_file)
            return True
        return False
    except Exception as e:
        print(f"Error saving decrypted PDF: {str(e)}")
        return False


def check_pdf_readability(pdf_path):
    """Check if a PDF file can be read and identify specific issues."""
    try:
        reader = PdfReader(pdf_path)

        # Check if PDF is encrypted
        if reader.is_encrypted:
            return False, "PDF is encrypted"

        # Check if PDF has pages
        if len(reader.pages) == 0:
            return False, "PDF has no pages"

        # Try to read the first page
        try:
            text = reader.pages[0].extract_text()
            if not text.strip():
                return False, "PDF appears to be empty or contains no text"
            return True, "PDF is readable"
        except Exception as e:
            return False, f"Error extracting text: {str(e)}"

    except Exception as e:
        return False, f"Error reading PDF file: {str(e)}"


def check_all_pdfs():
    """Check all PDF files in the reports directory."""
    # Get base directory
    base_dir = os.path.dirname(os.path.dirname(__file__))
    reports_dir = os.path.join(base_dir, "result", "csr_reports")

    results = []

    # Get all company directories
    company_dirs = [d for d in os.listdir(reports_dir) if os.path.isdir(os.path.join(reports_dir, d))]

    for company in tqdm(company_dirs, desc="Checking companies"):
        company_path = os.path.join(reports_dir, company)

        # Get all year directories
        year_dirs = [d for d in os.listdir(company_path) if os.path.isdir(os.path.join(company_path, d))]

        for year in year_dirs:
            year_path = os.path.join(company_path, year)

            # Find all PDF files in the year directory
            pdf_files = glob.glob(os.path.join(year_path, "*.pdf"))

            for pdf_file in pdf_files:
                is_readable, message = check_pdf_readability(pdf_file)
                results.append(
                    {
                        "company": company,
                        "year": year,
                        "filename": os.path.basename(pdf_file),
                        "is_readable": is_readable,
                        "message": message,
                        "file_size": os.path.getsize(pdf_file),  # Add file size for analysis
                    }
                )

    return results


def save_results_to_csv(results, output_file):
    """Save the PDF check results to a CSV file."""
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "company",
                "year",
                "filename",
                "is_readable",
                "message",
                "file_size",
            ],
        )
        writer.writeheader()
        writer.writerows(results)


def analyze_results(results):
    """Analyze and categorize the results."""
    issues = {
        "encrypted": [],
        "no_pages": [],
        "empty": [],
        "extraction_error": [],
        "reading_error": [],
        "other": [],
    }

    for result in results:
        if not result["is_readable"]:
            message = result["message"].lower()
            if "encrypted" in message:
                issues["encrypted"].append(result)
            elif "no pages" in message:
                issues["no_pages"].append(result)
            elif "empty" in message:
                issues["empty"].append(result)
            elif "extracting text" in message:
                issues["extraction_error"].append(result)
            elif "reading pdf" in message:
                issues["reading_error"].append(result)
            else:
                issues["other"].append(result)

    return issues


def main():
    """Main function to run the PDF checker."""
    print("Starting PDF readability check...")
    results = check_all_pdfs()

    # Save results
    output_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "result", "pdf_check_report.csv")
    save_results_to_csv(results, output_file)

    # Analyze results
    issues = analyze_results(results)

    # Print summary
    total_pdfs = len(results)
    readable_pdfs = sum(1 for r in results if r["is_readable"])
    unreadable_pdfs = total_pdfs - readable_pdfs

    print("\nPDF Check Summary:")
    print(f"Total PDFs checked: {total_pdfs}")
    print(f"Readable PDFs: {readable_pdfs}")
    print(f"Unreadable PDFs: {unreadable_pdfs}")

    if unreadable_pdfs > 0:
        print("\nDetailed Issues:")
        for issue_type, files in issues.items():
            if files:
                print(f"\n{issue_type.upper()} PDFs ({len(files)}):")
                for file in files:
                    print(f"- {file['company']}/{file['year']}/{file['filename']}")
                    print(f"  Size: {file['file_size']} bytes")
                    print(f"  Issue: {file['message']}")


if __name__ == "__main__":
    main()
