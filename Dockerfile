FROM python:3.12-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project
COPY . .



EXPOSE 8000

# Initialize DB tables then start the API
# Using python -m mcp.create_db to run the create_db.py module
# Add a small delay to ensure DB is fully ready (depends_on handles most of this)
CMD ["sh", "-c", "sleep 2 && python -m mcp.create_db && uvicorn mcp.app:app --host 0.0.0.0 --port 8000"]
