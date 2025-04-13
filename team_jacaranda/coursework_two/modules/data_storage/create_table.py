import psycopg2
from psycopg2.extras import execute_values

# --- PostgreSQL 配置 ---
db_config = {
    "dbname": "fift",
    "user": "postgres",
    "password": "postgres",
    "host": "host.docker.internal",
    "port": 5439
}

# --- 创建表并插入数据 ---
def create_table_and_insert_data():
    
    # 创建 CSR_indicators 表（指标表）
    create_indicators_table_sql = """
    CREATE TABLE IF NOT EXISTS csr_reporting.CSR_indicators (
        indicator_id SERIAL PRIMARY KEY,
        indicator_name VARCHAR(255),
        theme VARCHAR(100),
        unit VARCHAR(50),
        description TEXT,
        keywords TEXT[],
        is_target BOOLEAN
    );
    """
    
    # 创建 CSR_Data 表（数据记录表）
    create_data_table_sql = """
    CREATE TABLE IF NOT EXISTS csr_reporting.CSR_Data (
        data_id SERIAL PRIMARY KEY,
        security VARCHAR(255),
        report_year INT,
        indicator_id INT,
        indicator_name VARCHAR(255),
        value_raw TEXT,
        unit_raw VARCHAR(50),
        value_standardized NUMERIC,
        unit_standardized VARCHAR(50),
        source_excerpt JSONB,
        extraction_time TIMESTAMP,
        pdf_page TEXT,
        llm_response_raw TEXT,
        unit_conversion TEXT,
        FOREIGN KEY (indicator_id) REFERENCES csr_reporting.CSR_indicators (indicator_id)
    );
    """

    try:
        # 连接数据库并执行 SQL 语句
        conn = psycopg2.connect(**db_config)
        cur = conn.cursor()

        # 创建两张表
        cur.execute(create_indicators_table_sql)
        cur.execute(create_data_table_sql)
        conn.commit()

        print("✅ 表 CSR_indicators 和 CSR_Data 创建成功。")
    except Exception as e:
        print(f"❌ 出错了: {e}")

# --- 插入数据 ---
    # 原始指标关键词（供目标性指标复用）
    keywords_dict = {
        "Total GHG Emissions": ["Total GHG emissions", "Carbon emissions", "Greenhouse gas emissions", "CO₂ emissions", "GHG emissions"],
        "Carbon Intensity": ["Carbon intensity", "Carbon emissions per unit revenue", "Carbon emissions per dollar", "Emissions intensity", "GHG intensity"],
        "Renewable Energy Usage Ratio": ["Renewable energy usage", "Renewable energy ratio", "Solar energy usage", "Wind energy usage", "Percentage of renewable energy", "Green energy"],
        "Energy Intensity": ["Energy intensity", "Energy consumption per revenue", "Energy efficiency", "Energy usage per unit of output"],
        "Water Replenishment": ["Water replenishment", "Water recovery rate", "Water recycling rate", "Water return", "Water reinjection"],
        "Packaging Recyclable": ["Recyclable packaging", "Packaging recyclability", "Sustainable packaging", "Green packaging", "Recyclable materials", "Recyclable content in packaging", "Packaging recyclable content", "Recycled materials in packaging", "Recycled content"],
        "Waste Reduced": ["Waste reduction", "Waste prevented", "Waste prevention", "Waste minimization", "Waste avoidance", "Waste management", "Recycling rates"]
    }

    indicators_data = [
        # 🌍 Climate Change
        ("Total GHG Emissions", "Climate Change", "metric tons CO₂e",
         "衡量企业在生产、运营、供应链等过程中产生的温室气体总排放量，涵盖范围1（直接排放）、范围2（间接排放）、范围3（供应链排放）。",
         keywords_dict["Total GHG Emissions"], False),
        ("Total GHG Emissions Target", "Climate Change", None,
         "企业会设置温室气体排放的目标或降低目标（例如“到2030年减少20%”）。",
         keywords_dict["Total GHG Emissions"], True),
        ("Scope 1 Emissions", "Climate Change", "metric tons CO₂e", "范围1：企业直接排放的温室气体。", ["Scope 1"], False),
        ("Scope 2 Emissions", "Climate Change", "metric tons CO₂e", "范围2：企业间接能源使用所产生的排放。", ["Scope 2"], False),
        ("Scope 3 Emissions", "Climate Change", "metric tons CO₂e", "范围3：供应链相关的温室气体排放。", ["Scope 3"], False),
        ("Carbon Intensity", "Climate Change", "g CO₂e / $ revenue",
         "评估企业单位经济产出对应的碳排放量，有助于衡量企业的能源使用效率和环境影响。",
         keywords_dict["Carbon Intensity"], False),
        ("Carbon Intensity Target", "Climate Change", None,
         "企业设定减少碳强度的目标（例如“每年减少5%”）。",
         keywords_dict["Carbon Intensity"], True),
        ("Carbon Neutrality Target", "Climate Change", None,
         "企业设定的目标，通过减少排放和碳补偿来实现净零碳排放。",
         ["Carbon neutrality", "Net-zero carbon emissions", "Carbon offsetting", "Zero carbon target", "Carbon reduction targets"], True),

        # ⚡ Energy
        ("Renewable Energy Usage Ratio", "Energy", "%", "衡量企业在其总能源消费中，使用可再生能源的占比。",
         keywords_dict["Renewable Energy Usage Ratio"], False),
        ("Renewable Energy Usage Target", "Energy", None,
         "企业设定可再生能源使用比例的目标。",
         keywords_dict["Renewable Energy Usage Ratio"], True),
        ("Energy Intensity", "Energy", "kWh / $ revenue", "衡量单位经济产出对应的能源消耗量。",
         keywords_dict["Energy Intensity"], False),
        ("Energy Intensity Target", "Energy", None,
         "企业设定能源消耗强度的目标。",
         keywords_dict["Energy Intensity"], True),

        # 💧 Water Resources
        ("Water Reduction Target", "Water Resources", None,
         "企业设定的减少水资源使用的战略目标。",
         ["Water consumption reduction", "Water usage target", "Water reduction goals", "Water conservation targets"], True),
        ("Water Replenishment", "Water Resources", "%", "衡量企业使用水后有多少被回收或再引入环境。",
         keywords_dict["Water Replenishment"], False),
        ("Water Replenishment Target", "Water Resources", None,
         "水回收率目标。",
         keywords_dict["Water Replenishment"], True),

        # 📦 Packaging
        ("Packaging Recyclable", "Packaging", "%", "衡量产品包装中含有可回收成分的比例。",
         keywords_dict["Packaging Recyclable"], False),
        ("Packaging Recyclable Target", "Packaging", None,
         "企业设定可回收包装比例的目标。",
         keywords_dict["Packaging Recyclable"], True),

        # 🚮 Waste
        ("Waste Reduced", "Waste", "%", "衡量企业减少各类废弃物的情况。",
         keywords_dict["Waste Reduced"], False),
        ("Waste Reduction Target", "Waste", None,
         "企业设定减少废弃物的目标。",
         keywords_dict["Waste Reduced"], True)
    ]

    try:
        # 插入数据
        insert_sql = """
        INSERT INTO csr_reporting.CSR_indicators (indicator_name, theme, unit, description, keywords, is_target)
        VALUES %s;
        """
        execute_values(cur, insert_sql, indicators_data)
        conn.commit()

        print("✅ 表 CSR_indicators数据插入完成。")
    except Exception as e:
        print(f"❌ 出错了: {e}")
    finally:
        if conn:
            cur.close()
            conn.close()

if __name__ == "__main__":
    create_table_and_insert_data()
