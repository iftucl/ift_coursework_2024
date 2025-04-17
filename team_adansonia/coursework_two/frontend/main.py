from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import httpx

app = FastAPI()

app.mount("/static", StaticFiles(directory="team_adansonia/coursework_two/frontend/static"), name="static")
templates = Jinja2Templates(directory="team_adansonia/coursework_two/frontend/templates")

# Home page: search form
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})

# Company page: display fetched JSON
@app.get("/company/{symbol}", response_class=HTMLResponse)
async def company(request: Request, symbol: str):
    url = f"http://localhost:8081/companies/{symbol}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        data = response.json()
    return templates.TemplateResponse("company.html", {"request": request, "symbol": symbol, "data": data})

