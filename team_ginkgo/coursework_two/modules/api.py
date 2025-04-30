from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware  
from db import get_connection

app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"],   
)

@app.get("/reports")
def get_reports():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT symbol, company_name, report_year, scope_1, scope_2, scope_3, water_consumption
        FROM ginkgo.csr_reports_with_indicators
        ORDER BY symbol;
    """)
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    return [
        {
            "symbol": row[0],
            "company_name": row[1],
            "report_year": row[2],
            "scope_1": row[3],
            "scope_2": row[4],
            "scope_3": row[5],
            "water_consumption": row[6],
        }
        for row in results
    ]