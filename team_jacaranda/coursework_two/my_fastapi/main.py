"""
This module defines a FastAPI application that serves as an API for accessing CSR (Corporate Social Responsibility) data.
It includes endpoints for querying CSR indicators, CSR data, and company reports from a PostgreSQL database. 
Additionally, it serves static files for frontend development and includes CORS configuration for cross-origin requests.

Main functionality:
- CORS setup for allowing specific origins.
- Static file serving for frontend deployment (React).
- Database connections and query execution using psycopg2.
- API endpoints for accessing and querying CSR data, indicators, and reports.

To run the application:
- Run `poetry run uvicorn my_fastapi.main:app --host 0.0.0.0 --port 8000 --reload`
- Run `ngrok http --url=csr.jacaranda.ngrok.app 8000`
- Access Swagger UI at `http://127.0.0.1:8000/docs`
- Original JSON schema can be found at `http://127.0.0.1:8000/openapi.json`
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from typing import Optional
import psycopg2
import psycopg2.extras
import os

# === FastAPI instance setup ===
app = FastAPI(title="CSR Reporting API")

# === CORS configuration ===
origins = [
    "http://localhost:3000",       # React frontend development environment
    "https://example.com",         # Replace with the production environment if applicable
    "*"                            # Allow all origins during development (only for development use)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Static files configuration (for frontend deployment) ===
frontend_build_dir = os.path.join(os.path.dirname(__file__), "../modules/frontend/build")
if os.path.exists(frontend_build_dir):
    app.mount("/static", StaticFiles(directory=os.path.join(frontend_build_dir, "static")), name="static")

    @app.get("/")
    def serve_frontend():
        """
        Serves the React frontend's `index.html` file.

        This endpoint is used to serve the frontend React application after it has been built 
        and deployed to the server.

        :return: The `index.html` file of the React frontend.
        :rtype: FileResponse
        """
        return FileResponse(os.path.join(frontend_build_dir, "index.html"))

# === Favicon handling ===
favicon_path = os.path.join(frontend_build_dir, "favicon.ico")
if os.path.exists(favicon_path):
    @app.get("/favicon.ico")
    async def favicon():
        """
        Serves the `favicon.ico` file for the application.

        This endpoint handles requests for the favicon.ico, which is used as the browser icon.

        :return: The favicon.ico file.
        :rtype: FileResponse
        """
        return FileResponse(favicon_path)

# === Database configuration ===
db_config = {
    "dbname": "fift",
    "user": "postgres",
    "password": "postgres",
    "host": "host.docker.internal",
    "port": 5439
}

def get_db():
    """
    Establishes and returns a connection to the PostgreSQL database.

    This function connects to the database using the credentials and configuration defined
    in the `db_config` dictionary. It is used to execute queries against the database.

    :return: A database connection object.
    :rtype: psycopg2.extensions.connection
    """
    conn = psycopg2.connect(**db_config)
    return conn

def query_db(query: str, params: Optional[tuple] = None):
    """
    Executes a query on the database and returns the results.

    This function executes a given SQL query on the database using the provided parameters
    and returns the results as a list of dictionaries.

    :param query: The SQL query to execute.
    :type query: str
    :param params: Optional parameters to pass to the query, defaults to None.
    :type params: Optional[tuple]
    :return: The results of the query as a list of dictionaries.
    :rtype: list
    """
    conn = get_db()
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(query, params)
        results = cur.fetchall()
    conn.close()
    return results

# === CSR_indicators Endpoints ===

@app.get("/indicators")
def get_all_indicators():
    """
    Retrieves all CSR indicators from the database.

    This endpoint queries the `csr_reporting.CSR_indicators` table and returns all rows ordered by `indicator_id`.

    :return: A list of CSR indicators from the database.
    :rtype: list
    """
    query = "SELECT * FROM csr_reporting.CSR_indicators ORDER BY indicator_id;"
    return query_db(query)

@app.get("/indicators/search")
def search_indicators(indicator_name: Optional[str] = Query(None), theme: Optional[str] = Query(None)):
    """
    Searches CSR indicators based on optional query parameters.

    This endpoint allows filtering CSR indicators by name and/or theme. It queries the `csr_reporting.CSR_indicators`
    table and applies the provided filters.

    :param indicator_name: The name of the indicator to search for (optional).
    :type indicator_name: Optional[str]
    :param theme: The theme of the indicator to search for (optional).
    :type theme: Optional[str]
    :return: A list of filtered CSR indicators.
    :rtype: list
    """
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
    """
    Retrieves a specific CSR indicator by its ID.

    This endpoint queries the `csr_reporting.CSR_indicators` table for a record with the specified `indicator_id`.

    :param indicator_id: The ID of the indicator to retrieve.
    :type indicator_id: int
    :return: The CSR indicator with the specified ID.
    :rtype: dict
    :raises HTTPException: If no indicator is found with the given ID.
    """
    query = "SELECT * FROM csr_reporting.CSR_indicators WHERE indicator_id = %s;"
    results = query_db(query, (indicator_id,))
    if not results:
        raise HTTPException(status_code=404, detail="Indicator not found")
    return results[0]

# === CSR_Data Endpoints ===

@app.get("/data")
def get_all_data():
    """
    Retrieves all CSR data from the database.

    This endpoint queries the `csr_reporting.CSR_Data` table and returns the first 100 rows ordered by `data_id`.

    :return: A list of CSR data entries.
    :rtype: list
    """
    query = "SELECT * FROM csr_reporting.CSR_Data ORDER BY data_id LIMIT 100;"
    return query_db(query)

@app.get("/data/search")
def search_data(
    security: Optional[str] = Query(None),
    report_year: Optional[int] = Query(None),
    indicator_id: Optional[int] = Query(None),
    indicator_name: Optional[str] = Query(None)
):
    """
    Searches CSR data based on optional query parameters.

    This endpoint allows filtering CSR data by security, report year, indicator ID, and/or indicator name.

    :param security: The security of the data to search for (optional).
    :type security: Optional[str]
    :param report_year: The report year of the data to search for (optional).
    :type report_year: Optional[int]
    :param indicator_id: The ID of the indicator to search for (optional).
    :type indicator_id: Optional[int]
    :param indicator_name: The name of the indicator to search for (optional).
    :type indicator_name: Optional[str]
    :return: A list of filtered CSR data.
    :rtype: list
    """
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
    """
    Retrieves a specific CSR data entry by its ID.

    This endpoint queries the `csr_reporting.CSR_Data` table for a record with the specified `data_id`.

    :param data_id: The ID of the data entry to retrieve.
    :type data_id: int
    :return: The CSR data entry with the specified ID.
    :rtype: dict
    :raises HTTPException: If no data entry is found with the given ID.
    """
    query = "SELECT * FROM csr_reporting.CSR_Data WHERE data_id = %s;"
    results = query_db(query, (data_id,))
    if not results:
        raise HTTPException(status_code=404, detail="Data entry not found")
    return results[0]

# === Company Reports Endpoints ===

@app.get("/reports")
def get_all_company_reports():
    """
    Retrieves all company reports from the database.

    This endpoint queries the `csr_reporting.company_reports` table and returns all rows ordered by `id`.

    :return: A list of company reports.
    :rtype: list
    """
    query = "SELECT * FROM csr_reporting.company_reports ORDER BY id;"
    return query_db(query)

@app.get("/reports/search")
def search_reports(
    symbol: Optional[str] = Query(None),
    security: Optional[str] = Query(None),
    report_year: Optional[int] = Query(None)
):
    """
    Searches company reports based on optional query parameters.

    This endpoint allows filtering company reports by symbol, security, and/or report year.

    :param symbol: The symbol of the report to search for (optional).
    :type symbol: Optional[str]
    :param security: The security of the report to search for (optional).
    :type security: Optional[str]
    :param report_year: The report year of the report to search for (optional).
    :type report_year: Optional[int]
    :return: A list of filtered company reports.
    :rtype: list
    """
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
    """
    Retrieves a specific company report by its ID.

    This endpoint queries the `csr_reporting.company_reports` table for a record with the specified `report_id`.

    :param report_id: The ID of the company report to retrieve.
    :type report_id: int
    :return: The company report with the specified ID.
    :rtype: dict
    :raises HTTPException: If no company report is found with the given ID.
    """
    query = "SELECT * FROM csr_reporting.company_reports WHERE id = %s;"
    results = query_db(query, (report_id,))
    if not results:
        raise HTTPException(status_code=404, detail="Report not found")
    return results[0]
