import uvicorn
from fastapi import FastAPI, Depends, HTTPException
from pymongo.database import Database
from typing import Optional
from fastapi.encoders import jsonable_encoder
from team_adansonia.coursework_two.fast_api.db import get_db  # Adjust according to your actual folder structure
from fastapi import APIRouter, Depends, HTTPException
from pymongo.database import Database
from typing import Optional
import re
from team_adansonia.coursework_two.main import run_main_for_symbols
from team_adansonia.coursework_two.data_pipeline.csr_utils import get_latest_report_year

app = FastAPI()

@app.get("/companies/{symbol}")
async def get_company(symbol: str, year: Optional[str] = None, db: Database = Depends(get_db)):
    """
    Retrieves company ESG data by stock symbol.

    Args:
        symbol (str): The stock symbol of the company.
        year (Optional[str]): The specific year to filter ESG data (optional).
        db (Database): MongoDB database dependency.

    Returns:
        dict:
            - If `year` is provided: filtered ESG data for that year by category.
            - If `year` is not provided: full company record excluding MongoDB's _id field.

    Raises:
        HTTPException: 404 if the company is not found in the database.
    """
    print(f"🔔 Looking up company: {symbol}")  # Debug log

    # Access the 'companies' collection and exclude '_id' from the result
    company = db["companies"].find_one({"symbol": symbol.upper()}, {"_id": 0})  # Exclude _id field
    print(f"🔍 Company found: {company}")  # Debugging line to check the result

    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    if year:
        esg_data = {}
        for category, indicators in company.get("esg_data", {}).items():
            filtered = {
                k: v.get(year)
                for k, v in indicators.items()
                if isinstance(v, dict) and year in v
            }
            if filtered:
                esg_data[category] = filtered
        return {"symbol": symbol, "year": year, "esg_data": esg_data}

    return company

@app.get("/companies/v2/{symbol}")
async def get_company_new(symbol: str, year: Optional[str] = None, db: Database = Depends(get_db)):
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

@app.get("/all")
async def get_all_companies(db: Database = Depends(get_db)):
    companies = list(db["companies"].find({}, {"_id": 0}))
    return companies

if __name__ == "__main__":
    uvicorn.run("team_adansonia.coursework_two.fast_api.app:app", host="127.0.0.1", port=8081, reload=True)