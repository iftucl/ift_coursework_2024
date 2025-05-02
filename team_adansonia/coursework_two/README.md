# Team Adansonia Coursework 2

## Overview

This project is an end-to-end ESG (Environmental, Social, and Governance) data extraction and analysis pipeline. It automates the extraction of ESG data from company CSR (Corporate Social Responsibility) reports using AI-powered tools (LLaMA and DeepSeek), validates and processes the data, stores it in MongoDB, and exposes the results via a FastAPI backend and a simple frontend dashboard.

## Project Structure

```
coursework_two/
├── data_pipeline/      # PDF processing, AI extraction, and utilities
├── docs/               # Sphinx documentation
├── fast_api/           # FastAPI backend for ESG data API
├── frontend/           # FastAPI-based frontend dashboard
├── mongo-seed/         # MongoDB seed data
├── mongo_db/           # MongoDB connection and data logic
├── scheduler/          # (Optional) Jenkins or scheduling scripts
├── tests/              # Unit, integration, and E2E tests
├── utils/              # Utility scripts
├── validation/         # Data validation modules
├── Dockerfile          # Docker setup for the project
├── pyproject.toml      # Python dependencies (Poetry)
├── .env.template       # Example environment variables
└── main.py             # Main entry point for the data pipeline
```

## Key Components

- **Data Pipeline**: Extracts and processes ESG data from CSR PDFs using LLaMA and DeepSeek, then validates and stores results in MongoDB.
- **FastAPI Backend**: Exposes endpoints to query ESG data for companies.
- **Frontend**: Simple dashboard to search and view ESG data for companies.
- **MongoDB**: Stores company data, extracted ESG metrics, and goals.
- **Docker**: Containerizes the environment for reproducibility.

## Setup Instructions

### 1. Clone the Repository

```bash
git clone <repo-url>
cd Team_Adansonia/team_adansonia/coursework_two
```

### 2. Install Dependencies

- **Python**: Version 3.9 or 3.10 recommended.
- **Poetry**: For dependency management.

```bash
pip install poetry
poetry install
```

Or, for FastAPI backend only:

```bash
pip install -r fast_api/requirements.txt
```

### 3. Environment Variables

Copy `.env.template` to `.env` and fill in the required values:

```bash
cp .env.template .env
```

- Set your MongoDB URI, API keys, and root directory paths as needed.

### 4. MongoDB

Ensure MongoDB is running locally or update `MONGO_URI` in your `.env` file to point to your instance.

### 5. Running the Pipeline

To run the end-to-end ESG extraction pipeline for all companies:

```bash
poetry run python main.py
```

### 6. FastAPI Backend

Start the backend API (default: http://localhost:8081):

```bash
cd fast_api
uvicorn app:app --reload --port 8081
```

#### API Example

- `GET /companies/{symbol}`: Retrieve ESG data for a company (optionally by year).

### 7. Frontend Dashboard

Start the frontend (default: http://localhost:8080):

```bash
cd frontend
uvicorn main:app --reload --port 8080
```

- Make sure the backend is running at `http://localhost:8081` before starting the frontend.

### 8. Docker Setup

The project can be run using Docker Compose, which manages both the frontend and backend services.

#### Prerequisites

- Docker and Docker Compose installed
- MongoDB running from the outer docker-compose setup

#### Steps to Run

1. **Start MongoDB** (from the root directory):
```bash
cd /path/to/root
docker-compose up mongo_db
```

2. **Start the Application Services** (from coursework_two directory):
```bash
cd team_adansonia/coursework_two
docker-compose up --build
```

This will start:
- Frontend at http://localhost:5000
- Backend at http://localhost:8081
- MongoDB at mongodb://localhost:27019

#### Environment Variables

The Docker setup includes basic environment variables. To add more:
1. Copy `.env.template` to `.env`
2. Add your variables to the `environment` section in `docker-compose.yml`

#### Development Mode

For development with hot-reload:
1. Start MongoDB from outer docker-compose
2. Run backend locally: `python -m fast_api.app`
3. Run frontend locally: `python -m frontend.main`

#### Troubleshooting

- If services can't connect to MongoDB, ensure the network name in `docker-compose.yml` matches your outer compose network
- Check logs using: `docker-compose logs [service_name]`
- Rebuild services after dependency changes: `docker-compose up --build`

## Testing

Run all tests using pytest:

```