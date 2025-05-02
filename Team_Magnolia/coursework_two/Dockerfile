# Use a minimal official Python image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    POETRY_VERSION=1.8.1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        gcc \
        curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 - && \
    ln -s /root/.local/bin/poetry /usr/local/bin/poetry

# Create and set working directory
WORKDIR /app

# Copy only dependency files first (for better caching)
COPY pyproject.toml poetry.lock* /app/

# Install Python dependencies
RUN poetry install --no-dev --no-ansi

# Copy the rest of the application code
COPY . /app/

# Make the Main CLI entrypoint executable
RUN chmod +x /app/Main.py

# Default entrypoint: run the CLI
ENTRYPOINT ["poetry", "run", "python", "Main.py"]

# Default command: show help
CMD ["--help"]
