import os
import json
import psycopg2
from dotenv import load_dotenv
from tqdm import tqdm
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor, as_completed

# === 环境变量加载 ===
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../.env'))
load_dotenv(dotenv_path=env_path)
api_key = os.getenv("DEEPSEEK_API_KEY")
print("API Key Loaded:", api_key is not None)  # 检查是否加载成功

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

# === 查询需要标准化的记录（非目标性指标且 value_raw 不为空但 value_standardized 为空）===
def fetch_rows_to_standardize(conn):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT d.data_id, d.indicator_name, d.value_raw, d.unit_raw,
                   i.unit AS target_unit, i.description
            FROM csr_reporting.CSR_Data d
            JOIN csr_reporting.CSR_Indicators i ON d.indicator_id = i.indicator_id
            WHERE i.is_target = FALSE
              AND d.value_raw IS NOT NULL
              AND d.value_standardized IS NULL
        """)
        return cur.fetchall()

# === 提示词构建 ===
def build_conversion_prompt(indicator_name, description, value_raw, unit_raw, target_unit):
    return f"""你是一个擅长处理公司可持续发展报告中指标单位转换的智能助手。

该指标为“{indicator_name}”，其描述是：{description}

我们从报告中提取到该指标的原始值为：{value_raw} ，原始单位为：{unit_raw}。请你将其换算为目标单位“{target_unit}”。

请注意：
- 用英文输出；
- 如果单位无法转换（例如“tons”转为“%”），请将 convertibility 填写为 FALSE，将value_standardized 填写为 NULL；
- 如果单位可以转换，请将convertibility 填写为 TRUE，并进行单位换算，将换算后的值填入 value_standardized 字段（只填数值，不带单位）；
- 如果原始单位和目标单位意义相同或几乎相同，也请将 convertibility 填写为 true，value_standardized 填写为原始值；
- 请以如下格式返回结构化结果（不要添加任何其他内容，比如```json这样的前后缀，以下是一个结果示例）：
{{
  "convertibility": true,
  "value_standardized": "...",
  "note": "..."
}}
"""

# === 调用 DeepSeek API ===
def call_llm(prompt):
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "你是一个擅长处理公司可持续发展报告中指标单位转换的智能助手。"},
            {"role": "user", "content": prompt},
        ],
        stream=False,
    )
    return response.choices[0].message.content

# === 更新数据库结果（含 unit_conversion 备注） ===
def update_standardized(conn, data_id, value_standardized, unit_standardized, unit_conversion_note=None):
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE csr_reporting.CSR_Data
            SET value_standardized = %s,
                unit_standardized = %s,
                unit_conversion = %s
            WHERE data_id = %s
        """, (value_standardized, unit_standardized, unit_conversion_note, data_id))
    conn.commit()

# === 判断值是否合法数字 ===
def is_valid_number(value):
    try:
        float(value)
        return True
    except Exception:
        return False

# === 处理单条记录 ===
def process_row(conn, row):
    data_id, indicator_name, value_raw, unit_raw, target_unit, description = row

    try:
        # 情况 1：单位一致，直接填写
        if unit_raw and target_unit and unit_raw.strip().lower() == target_unit.strip().lower():
            update_standardized(conn, data_id, value_raw, target_unit, "单位一致，无需转换")
            print(f"✅ 数据 ID {data_id} 单位一致，已直接填入标准化值")
            return data_id

        # 情况 2：调用大模型判断是否能转换
        prompt = build_conversion_prompt(indicator_name, description, value_raw, unit_raw, target_unit)
        llm_response = call_llm(prompt)
        parsed = json.loads(llm_response)

        can_convert = parsed.get("convertibility", False)
        result_value = parsed.get("value_standardized")
        note = parsed.get("note", "")

        if not can_convert:
            update_standardized(conn, data_id, None, None, note)
            print(f"⚠️ 数据 ID {data_id} 单位无法转换，原因已记录：{note}")
            return None

        if not is_valid_number(result_value):
            raise ValueError(f"标准化结果非数字：{result_value}")

        update_standardized(conn, data_id, result_value, target_unit, note)
        print(f"✅ 数据 ID {data_id} 单位转换成功，标准化值为 {result_value}")
        return data_id

    except Exception as e:
        conn.rollback()
        print(f"❌ 数据 ID {data_id} 标准化失败：{e}")
        return None

# === 主函数 ===
def main():
    conn = get_connection()
    try:
        rows = fetch_rows_to_standardize(conn)
        print(f"共需标准化 {len(rows)} 条记录")

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(process_row, conn, row) for row in rows]

            for future in tqdm(as_completed(futures), total=len(futures), desc="标准化进度"):
                future.result()
    finally:
        conn.close()

if __name__ == "__main__":
    main()
