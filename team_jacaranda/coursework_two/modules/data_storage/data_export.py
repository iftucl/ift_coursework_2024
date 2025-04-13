import os
import pandas as pd
import psycopg2

# === 数据库配置 ===
db_config = {
    "dbname": "fift",
    "user": "postgres",
    "password": "postgres",
    "host": "host.docker.internal",
    "port": 5439
}

# === 导出路径设置：modules/db 目录 ===
script_dir = os.path.dirname(__file__)  # 当前脚本所在路径（modules/data_storage）
output_dir = os.path.abspath(os.path.join(script_dir, "../db"))  # 回到modules，然后进入db
os.makedirs(output_dir, exist_ok=True)

# === 导出函数 ===
def export_table_to_csv(table_name, output_path, conn):
    query = f"SELECT * FROM {table_name}"
    df = pd.read_sql_query(query, conn)
    df.to_csv(output_path, index=False)
    print(f"✅ 表 {table_name} 已成功导出到 {output_path}")

def main():
    conn = psycopg2.connect(**db_config)
    try:
        table_list = [
            ("csr_reporting.company_reports", os.path.join(output_dir, "company_reports.csv")),
            ("csr_reporting.csr_indicators", os.path.join(output_dir, "csr_indicators.csv")),
            ("csr_reporting.csr_data", os.path.join(output_dir, "csr_data.csv")),
        ]

        for table_name, csv_path in table_list:
            export_table_to_csv(table_name, csv_path, conn)

    finally:
        conn.close()

if __name__ == "__main__":
    main()
