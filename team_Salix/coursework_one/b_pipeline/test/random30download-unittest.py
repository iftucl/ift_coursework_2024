import os
import aiohttp
import asyncio
import pandas as pd
import random
import time
from tqdm.asyncio import tqdm
import nest_asyncio  # 兼容 Jupyter Notebook

nest_asyncio.apply()  # 适用于 Jupyter Notebook

BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # 取得當前腳本所在目錄
# 设置下载目录为 b_pipeline/test/downloaded_pdfs
DOWNLOAD_ROOT = os.getenv("DOWNLOAD_PATH", os.path.join(BASE_DIR, "downloaded_pdfs"))
os.makedirs(DOWNLOAD_ROOT, exist_ok=True)  # 確保目錄存在

# 打印路径用于调试
print(f"Files will be downloaded to: {DOWNLOAD_ROOT}")

# 读取 CSV 文件
CSV_PATH = os.getenv("CSV_PATH", os.path.join(BASE_DIR, "cleaned_url.csv"))
print(f"Looking for CSV at: {CSV_PATH}")

if not os.path.exists(CSV_PATH):
    raise FileNotFoundError(f"❌ 找不到 `{CSV_PATH}`，請確認文件是否存在！")

df = pd.read_csv(CSV_PATH)

# 确保需要的列存在
required_columns = {"company", "year", "url"}
if not required_columns.issubset(df.columns):
    raise ValueError(f"CSV 文件缺少必要的列: {required_columns - set(df.columns)}")

# 随机抽取 30 个 URL
df_sample = df.sample(n=30, random_state=42)

# 限制并发数（可调整）
MAX_CONCURRENT_DOWNLOADS = 10 # 一次下载一个
semaphore = asyncio.Semaphore(MAX_CONCURRENT_DOWNLOADS)

# 统计下载时间
download_times = []

# 失败日志文件 (TXT 格式)
LOG_FILE = "download_failed.txt"

# 添加 User-Agent & 伪装 Referer
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",  # Edge浏览器的UA
    "Referer": "https://www.bing.com/search",
    "Accept": "application/pdf,application/octet-stream",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive"
}

def log_failed_download(url, reason):
    """记录下载失败的 URL 和错误原因到 TXT 文件"""
    with open(LOG_FILE, "a", encoding="utf-8") as log_file:
        log_file.write(f"Failed: {url} | Reason: {reason}\n")

def log_statistics(stats_info):
    """将统计信息写入日志文件"""
    with open(LOG_FILE, "a", encoding="utf-8") as log_file:
        log_file.write("\n" + "="*50 + "\n")
        log_file.write("下载统计信息\n")
        log_file.write("="*50 + "\n")
        log_file.write(stats_info)
        log_file.write("\n" + "="*50 + "\n")

async def download_pdf(session, row, overall_progress):
    """下载 PDF 并保存到指定路径，带进度条，并记录失败日志"""
    company = row['company']
    year = str(row['year'])
    url = row['url']
    
    save_dir = os.path.join(DOWNLOAD_ROOT, company, year)
    save_path = os.path.join(save_dir, f"{company}_{year}.pdf")

    print(f"\n尝试下载: {company} {year}")
    print(f"URL: {url}")

    async with semaphore:
        start_time = time.time()

        try:
            async with session.get(url, headers=HEADERS) as response:
                if response.status == 200:
                    total_size = int(response.headers.get("content-length", 0))
                    chunk_size = 1024
                    downloaded = 0

                    # 创建单个文件的进度条
                    with tqdm(total=total_size, unit='B', unit_scale=True, 
                            desc=f"下载 {company}_{year}", leave=True) as file_progress:
                        
                        # 只有在 HTTP 200 时才创建目录
                        os.makedirs(save_dir, exist_ok=True)

                        with open(save_path, "wb") as f:
                            async for chunk in response.content.iter_chunked(chunk_size):
                                f.write(chunk)
                                downloaded += len(chunk)
                                file_progress.update(len(chunk))

                    download_time = time.time() - start_time
                    download_times.append({
                        'company': company,
                        'year': year,
                        'time': download_time,
                        'size': total_size
                    })
                    
                    speed = total_size / download_time / 1024 / 1024  # MB/s
                    print(f"✅ 成功下载: {save_path}")
                    print(f"   耗时: {download_time:.1f}秒, 速度: {speed:.2f}MB/s")
                    
                    overall_progress.update(1)
                    return True
                else:
                    error_msg = f"HTTP {response.status}"
                    print(f"❌ 下载失败: {error_msg}")
                    log_failed_download(url, error_msg)
                    return False

        except Exception as e:
            print(f"⚠️ 下载错误: {str(e)}")
            log_failed_download(url, str(e))
            return False

async def main():
    start_time = time.time()
    success_count = 0
    failed_count = 0
    
    async with aiohttp.ClientSession() as session:
        total_files = len(df_sample)
        
        # 创建总进度条
        with tqdm(total=total_files, desc="总进度", unit="file") as overall_progress:
            for _, row in df_sample.iterrows():
                try:
                    result = await download_pdf(session, row, overall_progress)
                    if result:
                        success_count += 1
                    else:
                        failed_count += 1
                    # 添加延迟避免请求过快
                    await asyncio.sleep(1)
                except Exception as e:
                    print(f"处理错误: {str(e)}")
                    failed_count += 1
                    continue
        
        # 打印统计信息
        total_time = time.time() - start_time
        print("\n📊 下载统计:")
        print(f"总文件数: {total_files}")
        print(f"成功下载: {success_count}")
        print(f"下载失败: {failed_count}")
        print(f"总耗时: {total_time:.1f}秒")
        
        if download_times:
            # 计算每个年份的平均下载时间
            year_stats = {}
            for item in download_times:
                year = item['year']
                if year not in year_stats:
                    year_stats[year] = {'times': [], 'sizes': []}
                year_stats[year]['times'].append(item['time'])
                year_stats[year]['sizes'].append(item['size'])
            
            # 收集统计信息
            stats = []
            stats.append("\n📊 下载统计:")
            stats.append(f"总文件数: {total_files}")
            stats.append(f"成功下载: {success_count}")
            stats.append(f"下载失败: {failed_count}")
            stats.append(f"总耗时: {total_time:.1f}秒")
            
            if download_times:
                # 各年份统计
                stats.append("\n📈 各年份下载统计:")
                for year in sorted(year_stats.keys()):
                    times = year_stats[year]['times']
                    sizes = year_stats[year]['sizes']
                    avg_time = sum(times) / len(times)
                    total_size = sum(sizes) / (1024 * 1024)
                    stats.append(f"\n{year}年:")
                    stats.append(f"  - 成功下载数量: {len(times)}份")
                    stats.append(f"  - 平均下载时间: {avg_time:.1f}秒")
                    stats.append(f"  - 总下载大小: {total_size:.1f}MB")
                    stats.append(f"  - 平均下载速度: {total_size/sum(times):.2f}MB/s")
                
                # 总体统计
                stats.append("\n📊 总体统计:")
                avg_time = sum(item['time'] for item in download_times) / len(download_times)
                total_size = sum(item['size'] for item in download_times) / (1024 * 1024)
                stats.append(f"平均下载时间: {avg_time:.1f}秒")
                stats.append(f"总下载大小: {total_size:.1f}MB")
                stats.append(f"平均下载速度: {total_size/total_time:.2f}MB/s")
                
                # 最快最慢记录
                fastest = min(download_times, key=lambda x: x['time'])
                slowest = max(download_times, key=lambda x: x['time'])
                stats.append(f"\n⚡️ 最快下载: {fastest['company']} ({fastest['year']}) - {fastest['time']:.1f}秒")
                stats.append(f"🐌 最慢下载: {slowest['company']} ({slowest['year']}) - {slowest['time']:.1f}秒")

            # 将统计信息写入日志文件
            stats_text = "\n".join(stats)
            print(stats_text)  # 打印到控制台
            log_statistics(stats_text)  # 写入日志文件
        
        # 检查下载失败日志
        if os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) > 0:
            print("\n⚠️ 下载失败的记录:")
            with open(LOG_FILE, 'r') as f:
                print(f.read())

if __name__ == "__main__":
    asyncio.run(main())
