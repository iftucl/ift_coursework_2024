"""
Sustainability Report Crawler
===========================

This module implements a web crawler for automatically finding and downloading sustainability reports
from company websites. It uses a combination of Bing search and direct webpage crawling to locate
PDF reports.

The crawler performs the following operations:
    1. Reads company names from an SQLite database
    2. For each company, searches for sustainability reports from 2019-2024
    3. Uses multiple search strategies to find PDF reports
    4. Saves results to a CSV file with URLs and metadata

Module Architecture
-----------------
The crawler uses a three-step strategy to find reports:
    1. Direct Bing search for PDF files
    2. Bing search for company sustainability webpages
    3. Crawling found webpages for PDF links

The module uses threading for parallel processing of different years for each company.

Dependencies
-----------
* External Libraries:
    - selenium: For web scraping and JavaScript rendering
    - requests: For HTTP requests and URL validation
    - pandas: For data manipulation
    - sqlite3: For database operations
    - urllib3: For HTTP operations
* Standard Libraries:
    - os: File and path operations
    - time: Time-related functions
    - datetime: Date and time operations
    - threading: Multi-threading support
    - concurrent.futures: Thread pool management
    - csv: CSV file operations
    - urllib.parse: URL parsing and encoding

Configuration
------------
The module uses several configuration constants:
    DB_PATH (str): Path to the SQLite database containing company names
    OUTPUT_DIR (str): Directory for saving results and logs
    LOG_FILENAME (str): Path to the log file

Example
-------
To use this module, ensure the SQLite database exists and run::

    $ python main.py

The script will automatically process all companies and save results to CSV.

Notes
-----
- The crawler implements rate limiting and error handling to be respectful to servers
- Multiple search strategies are used to maximize the chance of finding reports
- Results are saved incrementally to prevent data loss
- Extensive logging is implemented for debugging and monitoring

Author: Shijie Zhang
"""

import os
import time
import datetime
import urllib.parse
import threading
from concurrent.futures import ThreadPoolExecutor, wait, as_completed
import csv
import pandas as pd
import sqlite3

import requests
import urllib3
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

# Configuration
DB_PATH = os.path.join(os.path.dirname(__file__), 'Equity.db')  # Use correct case sensitivity
# If database is in another location, specify the full path
# DB_PATH = '/path/to/your/Equity.db'  # macOS/Linux
# DB_PATH = r'C:\path\to\your\Equity.db'  # Windows

# Disable warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Set output directory to a_pipeline/aresult
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "aresult")
os.makedirs(OUTPUT_DIR, exist_ok=True)  # Ensure output directory exists

# Initialize global variables
LOG_FILENAME = os.path.join(OUTPUT_DIR, f'crawler_log_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.txt')

def write_log(message: str) -> None:
    """
    Write a timestamped message to the log file.

    This function appends a message with a timestamp to the global log file. The timestamp
    format is 'YYYY-MM-DD HH:MM:SS'.

    Args:
        message (str): The message to write to the log file.

    Note:
        - The log file is created with the current timestamp when the module starts
        - Messages are appended with UTF-8 encoding
        - Each message is prefixed with a timestamp in brackets

    Example:
        >>> write_log("Processing started")
        # Writes: [2024-02-26 10:30:45] Processing started
    """
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(LOG_FILENAME, 'a', encoding='utf-8') as f:
        f.write(f"[{timestamp}] {message}\n")

def init_driver() -> webdriver.Chrome:
    """
    Initialize and configure a Chrome WebDriver for web scraping.

    This function sets up a Chrome WebDriver with specific options for headless operation
    and web scraping. It includes configurations for stability and mimicking a real browser.

    Returns:
        webdriver.Chrome: Configured Chrome WebDriver instance, or None if initialization fails.

    Note:
        The driver is configured with the following options:
            - Headless mode (no GUI)
            - GPU disabled
            - Sandbox disabled
            - Custom user agent
            - Dev-shm usage disabled

    Example:
        >>> driver = init_driver()
        >>> if driver:
        ...     driver.get("https://example.com")
        ...     driver.quit()
    """
    try:
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
        return webdriver.Chrome(options=options)
    except Exception as e:
        write_log(f"Failed to initialize Chrome driver: {str(e)}")
        return None

def get_search_results(driver: webdriver.Chrome, company_name: str, search_url: str, 
                      search_query: tuple, max_trials: int = 2) -> list:
    """
    Perform a search using Selenium and return the results.

    This function attempts to retrieve search results from a webpage using Selenium WebDriver.
    It includes retry logic for reliability.

    Args:
        driver (webdriver.Chrome): The Selenium WebDriver instance
        company_name (str): Name of the company being searched (for logging)
        search_url (str): URL to search
        search_query (tuple): Selenium locator tuple (By.X, "selector")
        max_trials (int, optional): Maximum number of retry attempts. Defaults to 2.

    Returns:
        list: List of WebElement objects representing search results, or None if failed

    Note:
        - Uses explicit wait with 15-second timeout
        - Implements retry logic with delays between attempts
        - Logs failures for debugging

    Example:
        >>> search_query = (By.CSS_SELECTOR, '.search-result')
        >>> results = get_search_results(driver, "Company", "http://example.com", search_query)
    """
    for trial in range(max_trials):
        try:
            driver.get(search_url)
            wait = WebDriverWait(driver, 15)
            
            search_results = wait.until(
                EC.presence_of_all_elements_located(search_query)
            )
            
            if search_results:
                return search_results
            time.sleep(1)

        except Exception as e:
            if trial < max_trials - 1:
                time.sleep(1)
                continue
            write_log(f"{company_name}: Failed to get search results: {str(e)}")
            return None
    
    return None

def check_pdf_url(url: str) -> bool:
    """
    Validate if a URL points to a valid PDF file.

    This function performs a HEAD request to check if a URL points to a valid PDF file.
    It follows redirects and verifies both the content type and URL extension.

    Args:
        url (str): URL to check

    Returns:
        bool: True if URL points to a valid PDF, False otherwise

    Note:
        - Uses HEAD request to minimize bandwidth usage
        - Follows redirects automatically
        - 5-second timeout for requests
        - Checks both response status and URL extension
        - Custom user agent to avoid blocking

    Example:
        >>> is_valid = check_pdf_url("http://example.com/report.pdf")
        >>> print(is_valid)
        True
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/pdf'
        }
        response = requests.head(url, headers=headers, allow_redirects=True, timeout=5)  # Reduced timeout
        
        if response.status_code == 200:
            final_url = response.url.lower()
            if '.pdf' in final_url:
                return True
        return False
        
    except Exception as e:
        write_log(f"Error checking URL {url}: {str(e)}")
        return False

def check_company_name_in_url(url: str, company_name: str) -> bool:
    """
    Check if a company name appears in a URL using fuzzy matching.

    This function implements a scoring system to determine if a company name is present
    in a URL. It handles multi-word company names and partial matches.

    Args:
        url (str): URL to check
        company_name (str): Company name to look for

    Returns:
        bool: True if company name is found in URL, False otherwise

    Note:
        Matching rules:
        - First word of company name must be present
        - For single-word names: requires exact match
        - For multi-word names: requires at least 50% of words to match
        - Case-insensitive matching

    Example:
        >>> found = check_company_name_in_url("http://apple-sustainability.com", "Apple Inc")
        >>> print(found)
        True
    """
    url_lower = url.lower()
    company_lower = company_name.lower()
    
    # Split company name into keywords
    company_keywords = company_lower.split()
    if not company_keywords:
        return False
        
    # First word must exist
    first_word = company_keywords[0]
    if first_word not in url_lower:
        return False
    
    # Calculate match score
    matched_words = sum(1 for word in company_keywords if word in url_lower)
    match_score = matched_words / len(company_keywords)
    
    # If only one word, require exact match
    if len(company_keywords) == 1:
        return match_score == 1
    
    # If multiple words, require at least 50% match
    return match_score >= 0.5

def check_url_year(url: str, target_year: int) -> bool:
    """
    Check if a URL contains the target year.

    This function searches for years (2010-2029) in the URL and verifies if the target
    year is present. If no year is found, it returns True to avoid false negatives.

    Args:
        url (str): URL to check
        target_year (int): Year to look for (e.g., 2024)

    Returns:
        bool: True if year is found or no year is present, False if different year found

    Note:
        - Uses regex pattern r'20[12]\d' to match years 2010-2029
        - Case-insensitive matching
        - Returns True if no year found in URL

    Example:
        >>> has_year = check_url_year("report-2024.pdf", 2024)
        >>> print(has_year)
        True
    """
    url_lower = url.lower()
    # Extract year (4 digits) from URL
    import re
    years_in_url = re.findall(r'20[12]\d', url_lower)  # Match years 2010-2029
    
    if years_in_url:
        # If URL contains year, check if it matches target year
        return str(target_year) in years_in_url
    return True  # If URL doesn't contain year, return True

def search_pdf_in_bing(driver: webdriver.Chrome, company_name: str, year: int) -> str:
    """
    Search for PDF reports directly using Bing search.

    This function performs a direct search for PDF sustainability reports using Bing.
    It tries multiple report types and implements various filtering criteria.

    Args:
        driver (webdriver.Chrome): Selenium WebDriver instance
        company_name (str): Name of the company
        year (int): Year of the report to search for

    Returns:
        str: URL of found PDF, or None if not found

    Note:
        Search strategy:
        - Tries multiple report type keywords
        - Excludes annual reports and specific websites
        - Validates PDF URLs
        - Checks company name presence
        - Verifies year matches
        - Limited to first 3 results per search

    Example:
        >>> url = search_pdf_in_bing(driver, "Apple", 2024)
        >>> if url:
        ...     print(f"Found PDF: {url}")
    """
    # Define possible report types
    report_types = [
        "sustainability report",
        "CSR report",
        "ESG report",
        "ESG disclosure",
        "ESG disclosure report",
        "global impact report",
        "ESG action report",
        "corporate responsibility report",
        "environmental report",
        "sustainable development report",
        "corporate citizenship report"
    ]
    
    # Try different report types
    for report_type in report_types:
        search_query = f"{company_name} {report_type} {year} pdf -responsibilityreports -\"annual report\""
        search_url = f"https://www.bing.com/search?q={urllib.parse.quote(search_query)}"
        write_log(f"{company_name}: Searching {report_type} for {year}")

        search_query = (By.CSS_SELECTOR, '.b_algo h2 a')
        search_results = get_search_results(driver, company_name, search_url, search_query)
        
        if not search_results:
            continue

        # Check results
        for result in search_results[:3]:
            url = result.get_attribute('href')
            if not url:
                continue
                
            url_lower = url.lower()
            if '.pdf' in url_lower:
                # Exclude annual report related URLs, case insensitive
                excluded_terms = ['annual', 'financial', 'proxy']
                if (not any(term in url_lower for term in excluded_terms) and 
                    check_url_year(url, year) and
                    check_company_name_in_url(url, company_name) and
                    check_pdf_url(url)):
                    return url
                
    return None

def search_webpage_in_bing(driver: webdriver.Chrome, company_name: str, year: int) -> list:
    """
    Search for company sustainability webpages using Bing.

    This function searches for company sustainability webpages that might contain
    PDF reports. It returns a list of potential webpage URLs to search.

    Args:
        driver (webdriver.Chrome): Selenium WebDriver instance
        company_name (str): Name of the company
        year (int): Year of the report to search for

    Returns:
        list: List of webpage URLs to search, or None if not found

    Note:
        Search strategy:
        - Uses multiple sustainability-related keywords
        - Excludes specific websites
        - Collects up to 3 non-PDF URLs per search
        - Implements logging for debugging
        - Handles timeouts and errors gracefully

    Example:
        >>> urls = search_webpage_in_bing(driver, "Apple", 2024)
        >>> if urls:
        ...     print(f"Found {len(urls)} pages to search")
    """
    # Define possible report types
    report_types = [
        "sustainability report",
        "CSR report",
        "ESG report",
        "ESG disclosure",
        "ESG disclosure report",
        "global impact report",
        "ESG action report",
        "corporate responsibility report",
        "environmental report",
        "sustainable development report"
    ]
    
    for report_type in report_types:
        search_query = f"{company_name} {report_type} {year} -responsibilityreports"
        search_url = f"https://www.bing.com/search?q={urllib.parse.quote(search_query)}"
        write_log(f"{company_name}: Searching webpage for {report_type} {year}")
            
        search_query = (By.CSS_SELECTOR, '.b_algo h2 a')
        search_results = get_search_results(driver, company_name, search_url, search_query)

        if not search_results:
            continue
        
        url_list = []
        count = 0
        for result in search_results:
            if count >= 3:
                break
            try:
                url = result.get_attribute('href')
                if url and '.pdf' not in url.lower():
                    url_list.append(url)
                    count += 1
            except Exception as e:
                write_log(f"{company_name}: Error getting URL: {str(e)}")
                continue

        if url_list:
            return url_list

    return None

def find_pdf_in_webpage(driver: webdriver.Chrome, company_name: str, url: str, year: int) -> str:
    """
    Search for PDF links within a webpage.

    This function scans a webpage for PDF links that match specific criteria for
    sustainability reports. It implements comprehensive filtering and validation.

    Args:
        driver (webdriver.Chrome): Selenium WebDriver instance
        company_name (str): Name of the company
        url (str): Webpage URL to search
        year (int): Year of the report to search for

    Returns:
        str: URL of found PDF, or None if not found

    Note:
        Search criteria:
        - Must be a PDF file
        - Must contain sustainability-related keywords
        - Must match target year
        - Must contain company name
        - Excludes annual reports and other irrelevant PDFs
        - Validates final PDF URL

    Example:
        >>> pdf_url = find_pdf_in_webpage(driver, "Apple", "https://example.com", 2024)
        >>> if pdf_url:
        ...     print(f"Found PDF: {pdf_url}")
    """
    write_log(f"{company_name}: Searching PDF in webpage for {year}")
    search_query = (By.TAG_NAME, "a")
    search_results = get_search_results(driver, company_name, url, search_query)

    if not search_results:
        write_log(f"{company_name}: No Search Results Found | URL: {url}")
        return None
    
    # Define possible keywords
    keywords = [
        'sustainability',
        'sustainable',
        'csr',
        'esg',
        'esg disclosure',
        'global impact',
        'environmental',
        'responsibility',
        'responsible',
        'climate',
        'disclosure',
        'corporate citizenship',
        'citizenship',
        'building america',
        'building'
    ]
    
    # Define excluded terms
    excluded_terms = ['annual', 'financial', 'proxy']
    
    for result in search_results:
        try:
            href = result.get_attribute('href')
            if not href:
                continue

            href_lower = href.lower()
            if '.pdf' in href_lower:
                # Exclude irrelevant PDFs
                if any(term in href_lower for term in excluded_terms):
                    continue
                
                # Check year and company name in URL
                if not check_url_year(href, year):
                    continue
                    
                if not check_company_name_in_url(href, company_name):
                    continue
                    
                text = result.text.lower()
                if str(year) in text and any(keyword.lower() in text for keyword in keywords):
                    if check_pdf_url(href):
                        return href
                
        except Exception:
            continue
    
    return None

def process_company_year(company_name, year):
    driver = init_driver()
    if not driver:
        return None, None
    
    try:
        # Try Bing search
        pdf_url = search_pdf_in_bing(driver, company_name, year)
        if pdf_url:
            driver.quit()
            return pdf_url, 'Bing direct search'
        
        # Try Bing webpage search
        webpage_urls = search_webpage_in_bing(driver, company_name, year)
        if webpage_urls:
            for url in webpage_urls:
                pdf_url = find_pdf_in_webpage(driver, company_name, url, year)
                if pdf_url:
                    driver.quit()
                    return pdf_url, 'Bing webpage search'
                    
    except Exception as e:
        write_log(f"Error processing {company_name} for {year}: {str(e)}")
    finally:
        driver.quit()
    
    return None, 'Not found'

def process_company(company_name: str) -> list:
    """
    Process a single company for all years.

    This function coordinates the search for sustainability reports across multiple years
    for a single company. It uses parallel processing for efficiency.

    Args:
        company_name (str): Name of the company to process

    Returns:
        list: List of dictionaries containing results for each year, sorted by year.
              Each dictionary contains:
              - company: Company name
              - year: Report year
              - url: Found URL or "Not found"
              - source: Source of the URL or "Not found"

    Note:
        - Uses ThreadPoolExecutor for parallel processing
        - Processes years 2019-2024 simultaneously
        - Maximum of 3 concurrent searches
        - Includes progress printing
        - Handles and logs errors

    Example:
        >>> results = process_company("Apple")
        >>> print(f"Found {len([r for r in results if r['url'] != 'Not found'])} reports")
    """
    print(f"\nProcessing company: {company_name}")
    results = []
    
    # Process all years in parallel
    with ThreadPoolExecutor(max_workers=3) as executor:  # Process 3 years simultaneously
        futures = {
            executor.submit(process_company_year, company_name, year): year 
            for year in range(2019, 2025)
        }
        
        for future in as_completed(futures):
            year = futures[future]
            try:
                url, source = future.result()
                results.append({
                    'company': company_name,
                    'year': year,
                    'url': url if url else 'Not found',
                    'source': source if source else 'Not found'
                })
                print(f"  {year}: {'Found' if url else 'Not found'}")
            except Exception as e:
                write_log(f"Error processing {company_name} for {year}: {str(e)}")
                results.append({
                    'company': company_name,
                    'year': year,
                    'url': 'Not found',
                    'source': 'Not found'
                })
    
    return sorted(results, key=lambda x: x['year'])  # Return results sorted by year

def process_companies(companies: list, results_file: str) -> None:
    """
    Process multiple companies and save results to CSV.

    This function coordinates the processing of multiple companies and manages the
    saving of results to a CSV file. Results are saved incrementally for safety.

    Args:
        companies (list): List of company names to process
        results_file (str): Path to save results CSV

    Note:
        - Creates CSV with headers: company, year, url, source
        - Saves results after each company is processed
        - Provides progress updates
        - UTF-8 encoding for file operations
        - Handles file writing safely

    Example:
        >>> companies = ["Apple", "Microsoft", "Google"]
        >>> process_companies(companies, "results.csv")
    """
    # Create results CSV with headers
    with open(results_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['company', 'year', 'url', 'source'])
        writer.writeheader()

    # Process each company
    for company in companies:
        company_results = process_company(company)
        
        # Save results for this company
        with open(results_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['company', 'year', 'url', 'source'])
            for result in company_results:
                writer.writerow(result)
        
        print(f"Completed processing {company}")

    print(f"\nProcessing completed. Results saved to {results_file}")

if __name__ == "__main__":
    try:
        # Read company names from SQLite database
        conn = sqlite3.connect(DB_PATH)
        
        # First list all table names
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print("Available tables in database:", [table[0] for table in tables])
        
        # Get structure of first table
        if tables:
            first_table = tables[0][0]
            cursor.execute(f"PRAGMA table_info({first_table})")
            columns = cursor.fetchall()
            print(f"\nColumns in table {first_table}:")
            for col in columns:
                print(f"- {col[1]}")  # col[1] is column name
        
        # Query using correct table name
        table_name = tables[0][0] if tables else None  # Use first table name
        if table_name:
            query = f"SELECT security FROM {table_name}"
            df = pd.read_sql_query(query, conn)
        
        conn.close()
        
        if 'security' not in df.columns:
            raise ValueError("Database must contain a 'security' column")
            
        companies = df['security'].tolist()
        print(f"Found {len(companies)} companies in database")
        
        # Create results filename
        results_file = os.path.join(OUTPUT_DIR, "results_dirty_urls.csv")
        
        # Process companies
        process_companies(companies, results_file)
        
        # Calculate processing statistics
        df_results = pd.read_csv(results_file)
        total_companies = len(companies)
        successful_companies = 0
        
        for company in companies:
            valid_urls = df_results[
                (df_results['company'] == company) & 
                (df_results['url'] != 'Not found')
            ].shape[0]
            
            if valid_urls >= 2:
                successful_companies += 1
                
        success_rate = (successful_companies / total_companies) * 100
        print(f"\nProcessing Summary:")
        print(f"Total Companies: {total_companies}")
        print(f"Successful Companies: {successful_companies}")
        print(f"Success Rate: {success_rate:.2f}%")
        
    except sqlite3.Error as e:
        print(f"Database error: {str(e)}")
    except Exception as e:
        print(f"Error: {str(e)}")
