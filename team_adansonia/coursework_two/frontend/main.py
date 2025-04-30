from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import httpx

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Home page: search form
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    url = f"http://localhost:8081/all"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        data = response.json()
    return templates.TemplateResponse("home.html", {"request": request, "data": data})

# Company page: display fetched JSON
@app.get("/company/{symbol}", response_class=HTMLResponse)
async def company(request: Request, symbol: str):
    """
    Fetches and displays the company data based on the given symbol by making an API call
    to the backend service. The data is then rendered on the 'company.html' page.

    Args:
        request: The HTTP request object passed by FastAPI for rendering templates.
        symbol: A string representing the company symbol to search for in the backend API.

    Returns:
        HTMLResponse: Renders the 'company.html' template with the company data fetched from the API.
    """
    url = f"http://localhost:8081/companies/{symbol}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        data = response.json()
    return templates.TemplateResponse("company.html", {"request": request, "symbol": symbol, "data": data})

