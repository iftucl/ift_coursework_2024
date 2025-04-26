# Access interface documentation:
# Automatically generate the Swagger of UI: http://127.0.0.1:8000/docs
# The original JSON Schema: http://127.0.0.1:8000/openapi.json

# poetry run uvicorn FastAPI.main:app --host 0.0.0.0 --port 8000 --reload
# ngrok http --url=csr.jacaranda.ngrok.app 8000

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from typing import Optional
import psycopg2
import psycopg2.extras
import os

app = FastAPI(title="CSR Reporting API")

# --- CORS配置 ---
origins = [
    "http://localhost:3000",       # React前端开发环境
    "https://example.com",         # 若有生产环境请替换
    "*"                            # 开发时允许全部（仅开发）
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 静态文件配置（用于生产环境部署React前端）---
frontend_build_dir = os.path.join(os.path.dirname(__file__), "../modules/frontend/build")
if os.path.exists(frontend_build_dir):
    app.mount("/static", StaticFiles(directory=os.path.join(frontend_build_dir, "static")), name="static")

    @app.get("/")
    def serve_frontend():
        return FileResponse(os.path.join(frontend_build_dir, "index.html"))

# 🔥 新增：专门处理 favicon.ico 请求
favicon_path = os.path.join(frontend_build_dir, "favicon.ico")
if os.path.exists(favicon_path):
    @app.get("/favicon.ico")
    async def favicon():
        return FileResponse(favicon_path)

# --- 数据库配置 ---
db_config = {
    "dbname": "fift",
    "user": "postgres",
    "password": "postgres",
    "host": "host.docker.internal",
    "port": 5439
}

def get_db():
    conn = psycopg2.connect(**db_config)
    return conn

def query_db(query: str, params: Optional[tuple] = None):
    conn = get_db()
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(query, params)
        results = cur.fetchall()
    conn.close()
    return results

# --- CSR_indicators Endpoints ---
@app.get("/indicators")
def get_all_indicators():
    query = "SELECT * FROM csr_reporting.CSR_indicators ORDER BY indicator_id;"
    return query_db(query)

@app.get("/indicators/search")
def search_indicators(indicator_name: Optional[str] = Query(None), theme: Optional[str] = Query(None)):
    query = "SELECT * FROM csr_reporting.CSR_indicators WHERE TRUE"
    params = []
    if indicator_name:
        query += " AND indicator_name ILIKE %s"
        params.append(f"%{indicator_name}%")
    if theme:
        query += " AND theme ILIKE %s"
        params.append(f"%{theme}%")
    return query_db(query, tuple(params))

@app.get("/indicators/{indicator_id}")
def get_indicator_by_id(indicator_id: int):
    query = "SELECT * FROM csr_reporting.CSR_indicators WHERE indicator_id = %s;"
    results = query_db(query, (indicator_id,))
    if not results:
        raise HTTPException(status_code=404, detail="Indicator not found")
    return results[0]

# --- CSR_Data Endpoints ---
@app.get("/data")
def get_all_data():
    query = "SELECT * FROM csr_reporting.CSR_Data ORDER BY data_id LIMIT 100;"
    return query_db(query)

@app.get("/data/search")
def search_data(
    security: Optional[str] = Query(None),
    report_year: Optional[int] = Query(None),
    indicator_id: Optional[int] = Query(None),
    indicator_name: Optional[str] = Query(None)
):
    query = "SELECT * FROM csr_reporting.CSR_Data WHERE TRUE"
    params = []
    if security:
        query += " AND security ILIKE %s"
        params.append(f"%{security}%")
    if report_year:
        query += " AND report_year = %s"
        params.append(report_year)
    if indicator_id:
        query += " AND indicator_id = %s"
        params.append(indicator_id)
    if indicator_name:
        query += " AND indicator_name ILIKE %s"
        params.append(f"%{indicator_name}%")
    query += " ORDER BY data_id LIMIT 100;"
    return query_db(query, tuple(params))

@app.get("/data/{data_id}")
def get_data_by_id(data_id: int):
    query = "SELECT * FROM csr_reporting.CSR_Data WHERE data_id = %s;"
    results = query_db(query, (data_id,))
    if not results:
        raise HTTPException(status_code=404, detail="Data entry not found")
    return results[0]

# --- company_reports Endpoints ---
@app.get("/reports")
def get_all_company_reports():
    query = "SELECT * FROM csr_reporting.company_reports ORDER BY id;"
    return query_db(query)

@app.get("/reports/search")
def search_reports(
    symbol: Optional[str] = Query(None),
    security: Optional[str] = Query(None),
    report_year: Optional[int] = Query(None)
):
    query = "SELECT * FROM csr_reporting.company_reports WHERE TRUE"
    params = []
    if symbol:
        query += " AND symbol ILIKE %s"
        params.append(f"%{symbol}%")
    if security:
        query += " AND security ILIKE %s"
        params.append(f"%{security}%")
    if report_year:
        query += " AND report_year = %s"
        params.append(report_year)
    query += " ORDER BY id;"
    return query_db(query, tuple(params))

@app.get("/reports/{report_id}")
def get_company_report_by_id(report_id: int):
    query = "SELECT * FROM csr_reporting.company_reports WHERE id = %s;"
    results = query_db(query, (report_id,))
    if not results:
        raise HTTPException(status_code=404, detail="Report not found")
    return results[0]
