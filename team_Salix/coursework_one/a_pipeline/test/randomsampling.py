import os
import time
import datetime
import urllib.parse
import threading
from concurrent.futures import ThreadPoolExecutor, wait, as_completed
import csv
import pandas as pd

import requests
import urllib3
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

# Disable warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 🚀 取得當前腳本所在的資料夾
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ✅ 自動尋找 CSV 文件
# 打印当前目录内容，用于调试
print(f"Current directory contents: {os.listdir(BASE_DIR)}")

CSV_PATH = os.getenv("CSV_PATH", os.path.join(BASE_DIR, "equitystatic.csv"))
CSV_PATH = os.path.normpath(CSV_PATH)  # 適配 Windows & macOS/Linux
print(f"Looking for CSV at: {CSV_PATH}")

# Initialize global variables
LOG_FILENAME = f'crawler_log_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'

# Helper Function: Write log
def write_log(message):
    """Write log with timestamp"""
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(LOG_FILENAME, 'a', encoding='utf-8') as f:
        f.write(f"[{timestamp}] {message}\n")

# Helper Function: Initialize Selenium WebDriver
def init_driver():
    """Initialize Selenium WebDriver"""
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

# Helper Function: Get search results using selenium
def get_search_results(driver, company_name, search_url, search_query, max_trials=2):
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

# Helper Function: Check PDF URL
def check_pdf_url(url):
    """检查 PDF URL 是否有效"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/pdf'
        }
        response = requests.head(url, headers=headers, allow_redirects=True, timeout=5)  # 减少超时时间
        
        if response.status_code == 200:
            final_url = response.url.lower()
            if '.pdf' in final_url:
                return True
        return False
        
    except Exception as e:
        write_log(f"Error checking URL {url}: {str(e)}")
        return False

# Helper Function: Check company name in URL
def check_company_name_in_url(url, company_name):
    """检查URL中是否包含公司名称（模糊匹配）"""
    url_lower = url.lower()
    company_lower = company_name.lower()
    
    # 将公司名称拆分成关键词
    company_keywords = company_lower.split()
    if not company_keywords:
        return False
        
    # 第一个单词必须存在
    first_word = company_keywords[0]
    if first_word not in url_lower:
        return False
    
    # 计算匹配度分数
    matched_words = sum(1 for word in company_keywords if word in url_lower)
    match_score = matched_words / len(company_keywords)
    
    # 如果只有一个单词，要求完全匹配
    if len(company_keywords) == 1:
        return match_score == 1
    
    # 如果有多个单词，要求至少50%的单词匹配
    return match_score >= 0.5

# Step 1: Try to search PDF directly in Bing
def search_pdf_in_bing(driver, company_name, year):
    # 定义可能的报告类型
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
        "corporate citizenship report",
        "building america report"
    ]
    
    # 尝试不同的报告类型搜索
    for report_type in report_types:
        search_query = f"{company_name} {report_type} {year} pdf -responsibilityreports -\"annual report\""
        search_url = f"https://www.bing.com/search?q={urllib.parse.quote(search_query)}"
        write_log(f"{company_name}: Searching {report_type} for {year}")

        search_query = (By.CSS_SELECTOR, '.b_algo h2 a')
        search_results = get_search_results(driver, company_name, search_url, search_query)
        
        if not search_results:
            continue

        # 检查结果
        for result in search_results[:3]:
            url = result.get_attribute('href')
            if not url:
                continue
                
            url_lower = url.lower()
            if '.pdf' in url_lower:
                # 排除年度报告相关的URL，不区分大小写
                excluded_terms = ['annual', 'financial', 'proxy']
                if (not any(term in url_lower for term in excluded_terms) and 
                    check_url_year(url, year) and
                    check_company_name_in_url(url, company_name) and
                    check_pdf_url(url)):
                    return url
                
    return None

# Step 2: If PDF not found directly in Bing, search company's sustainability website
def search_webpage_in_bing(driver, company_name, year):
    # 定义可能的报告类型
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

# Step 3: Find PDF links in company's sustainability website
def find_pdf_in_webpage(driver, company_name, url, year):
    write_log(f"{company_name}: Searching PDF in webpage for {year}")
    search_query = (By.TAG_NAME, "a")
    search_results = get_search_results(driver, company_name, url, search_query)

    if not search_results:
        write_log(f"{company_name}: No Search Results Found | URL: {url}")
        return None
    
    # 定义可能的关键词
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
    
    # 定义排除词
    excluded_terms = ['annual', 'financial', 'proxy']
    
    for result in search_results:
        try:
            href = result.get_attribute('href')
            if not href:
                continue

            href_lower = href.lower()
            if '.pdf' in href_lower:
                # 排除不相关的PDF
                if any(term in href_lower for term in excluded_terms):
                    continue
                
                # 检查URL中的年份和公司名称
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

# Process single company
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

def process_company(company_name):
    print(f"\nProcessing company: {company_name}")
    results = []
    
    # 并行处理所有年份
    with ThreadPoolExecutor(max_workers=3) as executor:  # 同时处理3个年份
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
    
    return sorted(results, key=lambda x: x['year'])  # 按年份排序返回结果

def process_companies(companies, results_file):
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

def check_url_year(url, target_year):
    """检查URL中的年份是否与目标年份匹配"""
    url_lower = url.lower()
    # 提取URL中的年份（4位数字）
    import re
    years_in_url = re.findall(r'20[12]\d', url_lower)  # 匹配2010-2029年
    
    if years_in_url:
        # 如果URL中包含年份，检查是否与目标年份匹配
        return str(target_year) in years_in_url
    return True  # 如果URL中没有年份，返回True

if __name__ == "__main__":
    try:
        # Read companies from CSV
        df = pd.read_csv(CSV_PATH)
        if 'security' not in df.columns:
            raise ValueError("CSV file must contain a 'security' column")
        
        # 随机抽取5家公司
        sample_companies = df['security'].sample(n=5).tolist()
        print(f"Randomly selected companies: {sample_companies}")
        
        # 创建结果文件名
        results_file = os.path.join(BASE_DIR, f'sample_results_{datetime.datetime.now().strftime("%Y%m%d")}.csv')
        
        # Process companies
        process_companies(sample_companies, results_file)
        
        # 检查每个公司的有效URL数量
        df_results = pd.read_csv(results_file)
        for company in sample_companies:
            valid_urls = df_results[
                (df_results['company'] == company) & 
                (df_results['url'] != 'Not found')
            ].shape[0]
            
            status = 'SUCCESS' if valid_urls >= 2 else 'FAILED'
            print(f"{company}: {valid_urls} valid URLs - {status}")
        
    except FileNotFoundError:
        print("Error: equitystatic.csv not found")
    except Exception as e:
        print(f"Error: {str(e)}")
