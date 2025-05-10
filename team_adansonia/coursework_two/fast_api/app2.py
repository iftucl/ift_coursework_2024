import uvicorn
from fastapi import FastAPI, Depends, HTTPException
from pymongo.database import Database
from typing import Optional
from fastapi.encoders import jsonable_encoder
from fast_api.db import get_db
from main import run_main_for_symbols
from data_pipeline.csr_utils import get_latest_report_year  # ✅ Import utility function

app = FastAPI()


@app.get("/companies/{symbol}")
async def get_company_new(symbol: str, year: Optional[str] = None, db: Database = Depends(get_db)):
    """
    Retrieve ESG (Environmental, Social, and Governance) data for a given company symbol.

    This endpoint attempts to retrieve the ESG data and goals for a company from the database.
    If the requested year is not provided, it uses the latest available CSR report year.
    If ESG data is missing, it attempts to refresh the data by running the pipeline.

    Parameters:
    - symbol (str): The ticker symbol of the company.
    - year (Optional[str]): The specific year for which ESG data is requested. If not provided, the latest year is used.
    - db (Database): The MongoDB database dependency injected via FastAPI.

    Returns:
    - dict: A dictionary containing the company symbol, year, ESG data, ESG goals, and other company metadata.

    Raises:
    - HTTPException: If the company is not found or if ESG data is unavailable.
    """
    symbol = symbol.upper()
    company = db["companies"].find_one({"symbol": symbol}, {"_id": 0})

    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    # Try to determine the target year from CSR report info
    csr_reports = company.get("csr_reports", {})
    target_year = int(year) if year else get_latest_report_year(csr_reports)

    if not target_year:
        raise HTTPException(status_code=404, detail=f"No valid CSR report years found for {symbol}")

    esg_data_key = f"esg_data_{target_year}"
    esg_goals_key = f"esg_goals_{target_year}"

    # If data for that year is missing, try to refresh
    if esg_data_key not in company:
        await run_main_for_symbols([(symbol, str(target_year))])
        company = db["companies"].find_one({"symbol": symbol}, {"_id": 0})

        if not company or esg_data_key not in company:
            raise HTTPException(status_code=404, detail=f"No ESG data found for {symbol} {target_year}")

    # Build final response with dynamic ESG keys included
    result = {
        "symbol": symbol,
        "year": target_year,
        esg_data_key: company.get(esg_data_key),
        esg_goals_key: company.get(esg_goals_key),
    }

    # Include other non-ESG fields
    for k, v in company.items():
        if not (k.startswith("esg_data_") or k.startswith("esg_goals_")):
            result[k] = v

    return result


if __name__ == "__main__":
    # Run the FastAPI application on localhost with port 8081
    uvicorn.run("team_adansonia.coursework_two.fast_api.app2:app", host="127.0.0.1", port=8081, reload=True)
