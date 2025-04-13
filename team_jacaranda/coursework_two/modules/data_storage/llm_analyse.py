import os
import psycopg2
import json
from dotenv import load_dotenv
from datetime import datetime
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

# === 环境变量加载 ===
env_path = os.path.abspath(os.path.join(__file__, '../../.env'))
load_dotenv(dotenv_path=env_path)
api_key = os.getenv("DEEPSEEK_API_KEY")

# === 初始化 LLM 客户端 ===
client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

# === PostgreSQL 配置 ===
db_config = {
    "dbname": "fift",
    "user": "postgres",
    "password": "postgres",
    "host": "host.docker.internal",
    "port": 5439
}

def get_connection():
    return psycopg2.connect(**db_config)

def fetch_pending_rows(conn):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT d.data_id, d.indicator_name, d.source_excerpt, d.indicator_id, d.report_year, 
                   i.description, i.is_target
            FROM csr_reporting.CSR_Data d
            JOIN csr_reporting.CSR_indicators i ON d.indicator_id = i.indicator_id
            WHERE d.value_raw IS NULL
        """)
        return cur.fetchall()

# === 提示词构建器 ===
def build_prompt(indicator_name, description, is_target, source_excerpt, report_year):
    # 将 source_excerpt 转换为适合模型的字符串格式
    formatted_paragraphs = "\n".join(
        f"(Page {item['page']}): {item['text']}" for item in source_excerpt
    )

    if is_target:
        return f"""你是一个负责分析企业可持续发展报告的专家。请你帮助识别与企业可持续发展目标相关的信息。

请从以下段落中找出与“{indicator_name}”这一目标相关的所有目标性描述内容。这些描述通常为计划、承诺、战略目标、长期愿景等。请将这些句子原文提取出来，作为该目标指标的原始值。

该指标的详细说明是：{description}

以下是报告中匹配到的段落（报告年份为 {report_year} 年）：
{formatted_paragraphs}

请只返回目标相关的原文句子（可以多句），以及相关的页码。请按以下格式返回（不要添加任何其他内容，比如```json这样的前后缀，以下是一个返回结果示例）：
{{ "value": "..." , "pages": ["page1", "page2"] }}
其中“value”为目标描述原文，"pages" 是该目标所在的页码列表。
"""

    else:
        return f"""你是一个擅长提取公司报告中指标数据的智能助手。

请从以下段落中找出与“{indicator_name}”相关的数值（如比例、数量、金额等）及其单位。该指标的详细说明是：{description}

请特别注意以下几点：
- 只提取与报告年份 {report_year} 年相关的数据；
- 请确保提取的单位与值一致；
- 请返回纯数字值，不要使用逗号分隔；
- 如果单位未直接写出，但能根据上下文推断（如“%”、“tons”等），也请填写（单位为%时也应该将单位写在unit里，而不是和数字一起）。

以下是报告中匹配到的段落（报告年份为 {report_year} 年）：
{formatted_paragraphs}

请以如下格式返回结构化结果（不要添加任何其他内容，比如```json这样的前后缀，以下是一个结果示例）：
{{
  "value": "55.3",
  "unit": "%",
  "note": "该值为{report_year}年实际可再生能源使用比例。",
  "pages": ["page1", "page2"]
}}
"""

# === 调用DeepSeek API ===
def call_llm(prompt):
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[ 
            {"role": "system", "content": "你是一个擅长提取企业可持续发展报告中关键指标的助手。"},
            {"role": "user", "content": prompt},
        ],
        stream=False
    )
    return response.choices[0].message.content

def update_result(conn, data_id, value_raw, unit_raw, llm_response_raw, pdf_page):
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE csr_reporting.CSR_Data
            SET value_raw = %s,
                unit_raw = %s,
                llm_response_raw = %s,
                pdf_page = %s
            WHERE data_id = %s
        """, (value_raw, unit_raw, llm_response_raw, pdf_page, data_id))
    conn.commit()

def is_valid_number(value):
    try:
        float(value)
        return True
    except ValueError:
        return False

def process_row(conn, row):
    data_id, indicator_name, source_excerpt, indicator_id, report_year, description, is_target = row

    try:
        # 提取 pdf 页码
        pdf_pages = [str(item['page']) for item in source_excerpt]

        # 构建 prompt & 调用 LLM
        prompt = build_prompt(indicator_name, description, is_target, source_excerpt, report_year)
        llm_output = call_llm(prompt)
        llm_response_raw = llm_output.strip()

        # === 目标性指标处理 ===
        if is_target:
            try:
                if isinstance(llm_output, str):
                    parsed = json.loads(llm_output)
                    value_raw = parsed.get("value")
                else:
                    value_raw = llm_output.strip()
            except json.JSONDecodeError:
                value_raw = llm_output.strip()
            unit_raw = None

        # === 非目标性指标处理 ===
        else:
            parsed = json.loads(llm_output)
            value_raw = parsed.get("value")
            unit_raw = parsed.get("unit")

            # 校验数值是否合法
            if value_raw and not is_valid_number(value_raw):
                raise ValueError(f"无效的数字值：{value_raw}")

        # === 更新数据库 ===
        update_result(conn, data_id, value_raw, unit_raw, llm_response_raw, ",".join(pdf_pages))
        return data_id

    except Exception as e:
        conn.rollback()  # 出错时一定要回滚事务
        print(f"❌ 数据 ID {data_id} 处理失败：{e}")
        raise  # 可选：继续向上传递异常，以便主程序记录失败

def main():
    conn = get_connection()
    try:
        rows = fetch_pending_rows(conn)
        print(f"共需处理 {len(rows)} 条记录")
        
        # 使用线程池和进度条
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(process_row, conn, row) for row in rows]
            
            # 使用 tqdm 显示进度条
            for future in tqdm(as_completed(futures), total=len(futures), desc="处理进度"):
                try:
                    future.result()
                    print("✅ 处理成功")
                except Exception as e:
                    print(f"❌ 处理失败：{e}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
