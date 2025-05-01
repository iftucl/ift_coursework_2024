import os
import fitz
import requests
import time
import glob
import shutil
import json
from concurrent.futures import ThreadPoolExecutor
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from config import DEEPSEEK_API_URL, DEEPSEEK_API_KEY
from db import get_connection

# Configuration
DOWNLOAD_DIR = os.path.abspath("downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Initialize Selenium Driver
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_experimental_option("prefs", {
    "download.default_directory": DOWNLOAD_DIR,
    "download.prompt_for_download": False,
    "plugins.always_open_pdf_externally": True
})
driver_service = Service(ChromeDriverManager().install())
global_driver = webdriver.Chrome(service=driver_service, options=chrome_options)

# Query reports to process
def fetch_reports_from_db(): ## delete limit 10 when upload to github
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT symbol, report_url, report_year
        FROM ginkgo.csr_reports_with_indicators
        WHERE report_url IS NOT NULL
        LIMIT 10;   
    """)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows

# Download PDF file
def try_requests_download(url, path):
    try:
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            with open(path, "wb") as f:
                f.write(r.content)
            print(f"requests download success: {os.path.basename(path)}")
            return True
        return False
    except Exception as e:
        print(f"requests exception: {e}")
        return False

def try_selenium_download(url, path):
    try:
        global_driver.get(url)
        time.sleep(6)
        elapsed = 0
        while elapsed < 30:
            time.sleep(2)
            pdfs = glob.glob(os.path.join(DOWNLOAD_DIR, "*.pdf"))
            if pdfs:
                newest = max(pdfs, key=os.path.getctime)
                shutil.move(newest, path)
                print(f"Selenium download success: {os.path.basename(path)}")
                return True
            elapsed += 2
    except Exception as e:
        print(f"Selenium exception: {e}")
    return False

def download_pdf(url, symbol, year):
    filename = f"{symbol}_{year}.pdf"
    save_path = os.path.join(DOWNLOAD_DIR, filename)
    if try_requests_download(url, save_path):
        return save_path
    elif try_selenium_download(url, save_path):
        return save_path
    print(f"Download failed: {url}")
    return None

# Call DeepSeek API
def call_deepseek_api(text):
    prompt = f"""The following is a section from a company's CSR report that includes Scope 1, Scope 2, Scope 3 emissions and Water Consumption.
Please extract the numerical values for Scope 1, Scope 2, Scope 3 (emissions) and Water Consumption. 

Regardless of whether the original unit is ton (tCO2), kilogram (kg CO2), megaton (Mt CO2), kiloton (kt CO2), or any other unit, 
please convert Scope 1, Scope 2, Scope 3 emissions into tCO2 (metric tons of carbon dioxide emissions).

For Water Consumption, regardless of whether the original unit is liters, cubic meters, gallons, etc., 
please convert it into Millions of Gallons (Mgal).

Return only the following JSON format, no explanation:
{{
    "scope_1": (number or 'none'),
    "scope_2": (number or 'none'),
    "scope_3": (number or 'none'),
    "water_consumption": (number or 'none')
}}

Text content:
{text}
"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
    }
    body = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "You are a professional sustainability report analysis assistant."},
            {"role": "user", "content": prompt}
        ]
    }
    try:
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=body, timeout=30)
        response.raise_for_status()
        content = response.json()['choices'][0]['message']['content']
        return content.strip().lstrip('`json').strip('`')
    except Exception as e:
        print(f"DeepSeek API call failed: {e}")
        return None

# Resolve real symbol
def resolve_real_symbol(symbol, year):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT symbol FROM ginkgo.csr_reports_with_indicators
        WHERE symbol ILIKE %s AND report_year = %s
        LIMIT 1;
    """, (f"%{symbol}%", year))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result[0] if result else None

# Update database
def update_database(symbol, year, scope_1, scope_2, scope_3, water_consumption):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        print(f"Updating database: symbol={symbol}, year={year}, scope_1={scope_1}, scope_2={scope_2}, scope_3={scope_3}, water_consumption={water_consumption}")
        cursor.execute("""
            UPDATE ginkgo.csr_reports_with_indicators
            SET scope_1 = %s,
                scope_2 = %s,
                scope_3 = %s,
                water_consumption = %s
            WHERE symbol = %s AND report_year = %s;
        """, (scope_1, scope_2, scope_3, water_consumption, symbol, year))
        print("cursor.rowcount =", cursor.rowcount)
        conn.commit()
        print(f"Update success: {symbol} - {year}")
    except Exception as e:
        conn.rollback()
        print(f"Database update failed: {e}")
    finally:
        cursor.close()
        conn.close()

# Main processing function
def process_single_download(row):
    symbol, url, year = row
    symbol = symbol.strip()
    print(f"\nProcessing: {symbol} - {year}")
    pdf_path = download_pdf(url, symbol, year)
    if not pdf_path:
        return

    try:
        with fitz.open(pdf_path) as doc:
            keywords = ["scope 1", "scope 2", "scope 3", "water consumption"]
            scope_pages = [
                doc[i].get_text()
                for i in range(len(doc))
                if any(keyword in doc[i].get_text().lower() for keyword in keywords)
            ]

    except Exception as e:
        print(f"PDF parse failed: {e}")
        return

    if not scope_pages:
        print(f"No scope-related pages found: {symbol} - {year}")
        return

    response = call_deepseek_api("\n".join(scope_pages))
    if not response:
        return

    try:
        result = json.loads(response)
        scope_1 = None if result['scope_1'] in ['null', 'none', ''] else float(result['scope_1'])
        scope_2 = None if result['scope_2'] in ['null', 'none', ''] else float(result['scope_2'])
        scope_3 = None if result.get('scope_3', 'none') in ['null', 'none', ''] else float(result['scope_3'])
        water_consumption = None if result.get('water_consumption', 'none') in ['null', 'none', ''] else float(
            result['water_consumption'])

        print(
            f"Extracted: scope_1={scope_1}, scope_2={scope_2}, scope_3={scope_3}, water_consumption={water_consumption}")

        real_symbol = resolve_real_symbol(symbol, year)
        if not real_symbol:
            print(f"Real symbol not found: {symbol} - {year}")
            return

        update_database(real_symbol, int(year), scope_1, scope_2, scope_3, water_consumption)
    except Exception as e:
        print(f"Parse failed: {e}")

    time.sleep(1)

# Entry point
def main():
    rows = fetch_reports_from_db()
    if not rows:
        print("No records to process")
        return

    print(f"Start processing {len(rows)} records...\n")
    with ThreadPoolExecutor(max_workers=3) as executor:
        executor.map(process_single_download, rows)

    global_driver.quit()
    print("All tasks completed")

if __name__ == "__main__":
    main()
