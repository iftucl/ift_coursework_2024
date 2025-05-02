#!/bin/bash

# Activate Python virtual environment (if applicable)
source .venv/bin/activate

# Check if MongoDB is running
echo "🔍 Checking MongoDB status..."
until nc -z localhost 27019; do
  echo "⏳ Waiting for MongoDB to be ready..."
  sleep 2
done
echo "✅ MongoDB is up and running!"

# Check if MinIO is running
echo "🔍 Checking MinIO status..."
until curl --output /dev/null --silent --head --fail http://localhost:9000/minio/health/live; do
  echo "⏳ Waiting for MinIO to be ready..."
  sleep 2
done
echo "✅ MinIO is up and running!"

# Start FastAPI server
echo "🚀 Starting FastAPI API..."
uvicorn modules.api.fastapi_api:app --host 0.0.0.0 --port 8000 --reload > logs/api.log 2>&1 &

# Verify FastAPI started successfully
sleep 3
if nc -z localhost 8000; then
  echo "✅ FastAPI API is running at http://localhost:8000"
else
  echo "❌ FastAPI failed to start. Check logs/api.log for details."
fi
