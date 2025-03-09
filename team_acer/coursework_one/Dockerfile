FROM python:3.11-bullseye

# Set environment variables for Poetry installation and configuration
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VERSION=1.6.1 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1

# Install system dependencies required for Poetry, Ollama, and Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl build-essential libffi-dev libssl-dev && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry

# Create a working directory for the application
WORKDIR /app

# Copy Poetry configuration files first to leverage Docker's caching mechanism
COPY pyproject.toml poetry.lock ./


# ✅ Install all Python dependencies
RUN poetry install --without dev --no-root

# ✅ Install Spacy & NLTK manually without modifying pyproject.toml
RUN poetry run pip install spacy nltk

# ✅ Now download Spacy models & NLTK stopwords
RUN poetry run python -m spacy download en_core_web_sm
RUN poetry run python -m nltk.downloader stopwords


# Copy the rest of the application code into the container
COPY . /app

# Expose FastAPI port
EXPOSE 8080

# Start FastAPI application with Uvicorn
CMD ["poetry", "run", "uvicorn", "a_pipeline.modules.fast_api.app:app", "--host", "0.0.0.0", "--port", "8080", "--reload"]