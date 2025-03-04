from fastapi import FastAPI
from modules.extracting_csr_reports.fetch_csr_reports import fetch_csr_reports

# =============================
#        FASTAPI APP
# =============================

app = FastAPI(
    title="CSR Report API",
    description="API to retrieve metadata and check availability of CSR reports",
    version="1.0.0",
)

# =============================
#       API ENDPOINTS
# =============================

@app.get("/")
def home():
    return {"message": "Welcome to the CSR Report API!"}

@app.get("/run-extraction/")
def run_extraction():
    """
    Manually trigger CSR report extraction.
    """
    fetch_csr_reports()
    return {"message": "CSR Report extraction started"}

# =============================
#        RUN FASTAPI
# =============================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080, reload=True)