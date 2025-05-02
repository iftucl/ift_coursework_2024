"""
CSR Report PDF Downloader

This module provides functionality for asynchronously downloading CSR (Corporate Social Responsibility) 
report PDFs from URLs specified in a JSON file(from COURSEWORK_ONE). It includes features for progress tracking, error logging,
and detailed download statistics.

The module uses asyncio and aiohttp for efficient concurrent downloads, with built-in rate limiting
to prevent overwhelming servers. It also includes comprehensive error handling and detailed logging
of both successful and failed downloads.

Example:
    To use the downloader::

        downloader = PDFDownloader()
        await downloader.download_pdfs()

The JSON file should contain a list of objects with the following fields:
    - company: Name of the company
    - year: Year of the CSR report
    - url: Download URL for the PDF
    - source: Source of the URL (e.g., Bing direct search)

Note:
    This script is compatible with Jupyter Notebook environments through the use of nest_asyncio.
"""

import asyncio
import os
import random
import time
from typing import Dict, List, Optional

import aiohttp
import nest_asyncio  # Compatible with Jupyter Notebook
import pandas as pd
from tqdm.asyncio import tqdm

nest_asyncio.apply()  # Apply for Jupyter Notebook


class PDFDownloader:
    def __init__(
        self, 
        json_path: Optional[str] = None, 
        download_root: Optional[str] = None
    ):
        """
        Initialize the PDFDownloader with configuration settings.

        Args:
            json_path (str, optional): Path to the JSON file containing download 
                                     information
            download_root (str, optional): Root directory for saving downloaded PDFs
        """
        # Configuration Constants
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.project_root = os.path.dirname(
            os.path.dirname(os.path.dirname(self.base_dir))
        )

        # Set paths
        self.json_path = json_path or os.getenv(
            "JSON_PATH",
            os.path.join(
                self.project_root, 
                "coursework_two", 
                "config", 
                "ref.json"
            ),
        )
        self.download_root = download_root or os.getenv(
            "DOWNLOAD_PATH",
            os.path.join(
                os.path.dirname(self.base_dir), 
                "result", 
                "csr_reports"
            ),
        )

        # Create download directory
        os.makedirs(self.download_root, exist_ok=True)

        # Download settings
        self.max_concurrent_downloads = 1
        self.semaphore = asyncio.Semaphore(self.max_concurrent_downloads)
        self.download_times: List[Dict] = []
        self.log_file = "download_failed.txt"

        # Headers for requests
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"
            ),
            "Referer": "https://www.bing.com/search",
            "Accept": "application/pdf,application/octet-stream",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
        }

        # Load and validate JSON data if no data is provided
        self.df = None

    def _load_and_validate_data(self) -> None:
        """
        Load and validate the JSON data containing download information.

        This method:
        1. Checks if the JSON file exists
        2. Loads the data into a pandas DataFrame
        3. Validates that all required columns are present

        Raises:
            FileNotFoundError: If the JSON file does not exist
            ValueError: If required columns are missing from the JSON data
        """
        if not os.path.exists(self.json_path):
            raise FileNotFoundError(f"❌ Cannot find `{self.json_path}`, please check if the file exists!")

        self.df = pd.read_json(self.json_path)

        # Ensure required columns exist
        required_columns = {"company", "year", "url"}
        if not required_columns.issubset(self.df.columns):
            raise ValueError(f"JSON file missing required columns: {required_columns - set(self.df.columns)}")

    def log_failed_download(self, url: str, reason: str) -> None:
        """
        Log failed download attempts to a text file.

        Args:
            url (str): The URL that failed to download
            reason (str): The reason for the download failure

        The log entry is formatted as: "Failed: {url} | Reason: {reason}"
        """
        with open(self.log_file, "a", encoding="utf-8") as log_file:
            log_file.write(f"Failed: {url} | Reason: {reason}\n")

    def log_statistics(self, stats_info: str) -> None:
        """
        Write download statistics to the log file.

        Args:
            stats_info (str): Formatted string containing download statistics

        The statistics are written with a header and footer of '=' characters
        for better readability in the log file.
        """
        with open(self.log_file, "a", encoding="utf-8") as log_file:
            log_file.write("\n" + "=" * 50 + "\n")
            log_file.write("Download Statistics\n")
            log_file.write("=" * 50 + "\n")
            log_file.write(stats_info)
            log_file.write("\n" + "=" * 50 + "\n")

    async def download_pdf(self, session: aiohttp.ClientSession, row: pd.Series, overall_progress: tqdm) -> bool:
        """
        Download a single PDF file asynchronously.

        Args:
            session (aiohttp.ClientSession): The aiohttp client session for making HTTP requests
            row (pd.Series): A row from the DataFrame containing download information
            overall_progress (tqdm): Progress bar for tracking overall download progress

        Returns:
            bool: True if download was successful, False otherwise

        This method:
        1. Creates the appropriate directory structure for saving the file
        2. Downloads the file with progress tracking
        3. Handles errors and logs failures
        4. Adds random delays between downloads to prevent rate limiting
        """
        company = row["company"]
        year = str(row["year"])
        url = row["url"]

        save_dir = os.path.join(self.download_root, company, year)
        save_path = os.path.join(save_dir, f"{company}_{year}.pdf")

        print(f"\nAttempting to download: {company} {year}")
        print(f"URL: {url}")

        async with self.semaphore:
            start_time = time.time()

            try:
                async with session.get(url, headers=self.headers) as response:
                    if response.status == 200:
                        total_size = int(response.headers.get("content-length", 0))
                        chunk_size = 1024
                        downloaded = 0

                        with tqdm(
                            total=total_size,
                            unit="B",
                            unit_scale=True,
                            desc=f"Downloading {company}_{year}",
                            leave=True,
                        ) as file_progress:
                            os.makedirs(save_dir, exist_ok=True)

                            with open(save_path, "wb") as f:
                                async for chunk in response.content.iter_chunked(chunk_size):
                                    f.write(chunk)
                                    downloaded += len(chunk)
                                    file_progress.update(len(chunk))

                        download_time = time.time() - start_time
                        self.download_times.append(
                            {
                                "company": company,
                                "year": year,
                                "time": download_time,
                                "size": total_size,
                            }
                        )

                        speed = total_size / download_time / 1024 / 1024  # MB/s
                        print(f"✅ Successfully downloaded: {save_path}")
                        print(f"   Time: {download_time:.1f}s, Speed: {speed:.2f}MB/s")

                        if overall_progress is not None:
                            overall_progress.update(1)
                        return True
                    else:
                        error_msg = f"HTTP {response.status}: {response.reason}"
                        print(f"❌ Download failed: {error_msg}")
                        self.log_failed_download(url, error_msg)
                        if overall_progress is not None:
                            overall_progress.update(1)
                        return False

            except Exception as e:
                error_msg = f"Error: {str(e)}"
                print(f"❌ Download failed: {error_msg}")
                self.log_failed_download(url, error_msg)
                if overall_progress is not None:
                    overall_progress.update(1)
                return False

            finally:
                # Add random delay between downloads (1-3 seconds)
                await asyncio.sleep(random.uniform(1, 3))

    async def download_pdfs(self, data: Optional[List[Dict]] = None) -> None:
        """
        Download all PDFs from the configured JSON file or provided data.

        Args:
            data (List[Dict], optional): List of dictionaries containing download information.
                                      If not provided, data will be loaded from the JSON file.

        This method:
        1. Loads and validates the data if not provided
        2. Creates an aiohttp session for concurrent downloads
        3. Tracks overall progress with a progress bar
        4. Gathers statistics about successful and failed downloads
        5. Logs the final statistics

        Raises:
            ValueError: If required columns are missing from the data
        """
        if data is not None:
            self.df = pd.DataFrame(data)
        elif self.df is None:
            self._load_and_validate_data()

        # Ensure required columns exist
        required_columns = {"company", "year", "url"}
        if not required_columns.issubset(self.df.columns):
            raise ValueError(f"Data missing required columns: {required_columns - set(self.df.columns)}")

        total_files = len(self.df)
        successful_downloads = 0
        failed_downloads = 0

        async with aiohttp.ClientSession() as session:
            with tqdm(total=total_files, desc="Overall Progress", unit="file") as progress:
                tasks = []
                for _, row in self.df.iterrows():
                    task = asyncio.create_task(self.download_pdf(session, row, progress))
                    tasks.append(task)

                results = await asyncio.gather(*tasks)
                successful_downloads = sum(1 for r in results if r)
                failed_downloads = sum(1 for r in results if not r)

        # Calculate and log statistics
        total_time = sum(d["time"] for d in self.download_times)
        total_size = sum(d["size"] for d in self.download_times)
        avg_speed = total_size / total_time / 1024 / 1024 if total_time > 0 else 0

        stats = (
            f"Total files: {total_files}\n"
            f"Successful: {successful_downloads}\n"
            f"Failed: {failed_downloads}\n"
            f"Total time: {total_time:.1f}s\n"
            f"Average speed: {avg_speed:.2f}MB/s"
        )
        print("\n" + stats)
        self.log_statistics(stats)


if __name__ == "__main__":
    downloader = PDFDownloader()
    asyncio.run(downloader.download_pdfs())
