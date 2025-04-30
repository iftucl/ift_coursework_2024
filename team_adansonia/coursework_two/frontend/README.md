## Prerequisites

Make sure the following are running before starting the frontend:

1. **Docker is running**

2. **FastAPI backend is running at** `http://localhost:8801`

   (This should expose the route: `GET /companies/{symbol}`)

How to start the fronend independently, make sure you are in the root directory

then run

```zsh
cd team_adansonia/coursework_two/frontend && uvicorn main:app --reload --port 8080
```