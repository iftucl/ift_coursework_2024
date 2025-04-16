import uvicorn
from fastapi import FastAPI, Depends, HTTPException
from pymongo.database import Database
from typing import Optional
from fastapi.encoders import jsonable_encoder
from team_adansonia.coursework_two.fast_api.db import get_db  # Adjust according to your actual folder structure

app = FastAPI()

@app.get("/companies/{symbol}")
async def get_company(symbol: str, year: Optional[str] = None, db: Database = Depends(get_db)):
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

if __name__ == "__main__":
    uvicorn.run("team_adansonia.coursework_two.fast_api.app:app", host="127.0.0.1", port=8081, reload=True)