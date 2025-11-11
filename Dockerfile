FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Initialize DB tables then start the API
CMD ["sh", "-c", "python -m mcp.create_db && uvicorn mcp.app:app --host 0.0.0.0 --port 8000"]