# Use official Python image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory inside the container
WORKDIR /app

# Copy everything into the container
COPY . /app

# Install dependencies
RUN pip install --upgrade pip && \
    pip install fastapi uvicorn pymongo python-dotenv

# Expose the port FastAPI will run on
EXPOSE 8000

# Set the command to run the app
CMD ["uvicorn", "fast_api.app:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
