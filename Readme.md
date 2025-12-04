# Middleware server connecting LLM and Expertiza

Lightweight middleware built with **FastAPI** that connects a large language model (LLM) to the Expertiza review platform. Provides async endpoints, JWT auth, and PostgreSQL persistence.

---

##  Documentation (GitHub Wiki)

Full documentation, including architecture, setup guides, API reference, and data models, is available here:

 **https://github.com/krishapatel10/middleware/wiki**

Key pages:

- [01 — Introduction & Overview](../../wiki/01-Introduction)
- [02 — Getting Started](../../wiki/02-Getting-Started)
- [03 — Architecture](../../wiki/03-Architecture)
- [04 — API: Reviews](../../wiki/04-API-Reviews)
- [05 — API: LLM](../../wiki/05-API-LLM)
- [API Authentication](../../wiki/04-API-Auth)
- [API Error Handling](../../wiki/04-API-Errors)
- [Data Model](../../wiki/05-Data-Model)

---

## Tech Stack

* **FastAPI** – modern async web framework  
* **PostgreSQL** – relational database  
* **SQLAlchemy + asyncpg** – ORM and async DB driver  
* **Uvicorn** – ASGI server  

---

**Notes**

psql is not a pip package — install PostgreSQL locally if running without Docker.
Always use a strong JWT_SECRET in production.


