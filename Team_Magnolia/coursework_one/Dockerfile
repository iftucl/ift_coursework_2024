# Use Python 3.10-bullseye as the base image
FROM python:3.10-bullseye

# Set environment variables for Poetry installation and configuration
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VERSION=1.6.1 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1

# Install system dependencies required for Poetry and Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl build-essential libffi-dev libssl-dev && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry

# Create a working directory for the application
WORKDIR /app

# Copy Poetry configuration files first to leverage Docker's caching mechanism
COPY pyproject.toml ./

# Generate a fresh poetry.lock file and install dependencies
RUN poetry lock && poetry install

# Download NLTK data for text processing
RUN poetry run python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords')"

# Copy the rest of the application code into the container
COPY . .

# Expose necessary ports
# FastAPI - Used by fastapi_api.py for API access
EXPOSE 8000
# Streamlit - Used by streamlit_app.py for dashboard access
EXPOSE 8501

# Default command: keep container alive until a command is executed manually
CMD ["sleep", "infinity"]