# Middleware server connecting LLM and Expertiza

Lightweight middleware built with **FastAPI** that connects a large language model (LLM) to the Expertiza review platform. Provides async endpoints, JWT auth, and PostgreSQL persistence.

---

## Tech Stack

* **FastAPI** – modern async web framework
* **PostgreSQL** – relational database
* **SQLAlchemy + asyncpg** – ORM and async DB driver
* **Uvicorn** – ASGI server

---

## Setup

### 1. Clone and install

```bash
git clone https://github.ncsu.edu/upaul/mcp-server.git
cd mcp-server
pip install -r requirements.txt
```

### 2. Environment variables

Create a `.env` file in project root:

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/reviews_db
JWT_SECRET_KEY=your_secret_key
JWT_ALGORITHM=HS256
```

### 3. Create the database (local dev)

Run the provided script to create DB schema/tables:

```bash
python create_db.py
```


### 4. Run the app

```bash
uvicorn mcp.app:app --reload
```

---

## API Endpoints

Reviews
```
POST /reviews
Create a review (body: ReviewPayload). Background job will schedule LLM processing.
Response: ReviewResponse (201)
GET /reviews/{review_id}
Retrieve a review by ID. Response: ReviewResponse.
POST /reviews/{review_id}/accept
Finalize a review (body: FinalizeReview — finalized score & feedback). Response: ReviewResponse.
POST /reviews/{review_id}/trigger
Manually schedule/reprocess LLM job for an existing review. Returns { message, status, review_id } (202).
```

LLM service (internal/admin)

```
POST /llmreview
Calls LLMService to evaluate & parse review_text. Body: ReviewRequest (fields: review_text, optional temperature, optional max_attempts). Returns validated JSON or 422/502 on errors.
```

---


## Notes

* `psql` (the PostgreSQL CLI) is not a pip package — ensure PostgreSQL is installed on your system.
* Replace `your_secret_key` with a secure key in production.

