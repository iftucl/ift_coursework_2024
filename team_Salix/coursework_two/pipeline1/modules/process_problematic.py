import os

import pandas as pd


def delete_files(files_df, source_dir):
    """
    Delete specified files

    Args:
        files_df (pd.DataFrame): DataFrame containing file information
        source_dir (str): Source directory path

    Returns:
        tuple: (found_count, deleted_count, errors)
    """
    found_count = len(files_df)
    deleted_count = 0
    errors = []

    for _, row in files_df.iterrows():
        # Build complete file path including company and year directories
        file_path = os.path.join(source_dir, row["company"], str(row["year"]), row["filename"])

        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                deleted_count += 1

                # If directory is empty, delete the directory
                year_dir = os.path.dirname(file_path)
                company_dir = os.path.dirname(year_dir)

                if os.path.exists(year_dir) and not os.listdir(year_dir):
                    os.rmdir(year_dir)
                if os.path.exists(company_dir) and not os.listdir(company_dir):
                    os.rmdir(company_dir)
            else:
                errors.append(f"File does not exist: {file_path}")
        except Exception as e:
            errors.append(f"Error deleting file {file_path}: {str(e)}")

    return found_count, deleted_count, errors


def process_problematic_files():
    """
    Process problematic PDF files
    1. Delete encrypted PDF files
    2. Delete empty PDF files
    3. Generate processing report
    """
    # Define directories
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    source_dir = os.path.join(base_dir, "result", "csr_reports")
    result_dir = os.path.join(base_dir, "result")

    # Read check report
    report_path = os.path.join(result_dir, "pdf_check_report.csv")
    if not os.path.exists(report_path):
        raise FileNotFoundError(f"Check report does not exist: {report_path}")

    df = pd.read_csv(report_path)

    # Filter encrypted and empty files
    encrypted_files = df[df["message"] == "PDF is encrypted"]
    empty_files = df[df["message"] == "PDF appears to be empty or contains no text"]

    # Delete files
    encrypted_stats = delete_files(encrypted_files, source_dir)
    empty_stats = delete_files(empty_files, source_dir)

    # Generate summary
    summary = {
        "file_type": ["Encrypted", "Empty"],
        "files_found": [encrypted_stats[0], empty_stats[0]],
        "files_deleted": [encrypted_stats[1], empty_stats[1]],
        "errors": [len(encrypted_stats[2]), len(empty_stats[2])],
    }

    summary_df = pd.DataFrame(summary)
    summary_path = os.path.join(result_dir, "deletion_summary.csv")
    os.makedirs(os.path.dirname(summary_path), exist_ok=True)
    summary_df.to_csv(summary_path, index=False)

    # Print results
    print("\nProcessing Summary:")
    print(f"Encrypted files: Found {encrypted_stats[0]}, Deleted {encrypted_stats[1]}")
    print(f"Empty files: Found {empty_stats[0]}, Deleted {empty_stats[1]}")

    if encrypted_stats[2] or empty_stats[2]:
        print("\nEncountered errors:")
        for error in encrypted_stats[2] + empty_stats[2]:
            print(f"- {error}")

    print(f"\nSummary saved to: {summary_path}")


if __name__ == "__main__":
    process_problematic_files()
