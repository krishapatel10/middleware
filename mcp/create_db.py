# create_db.py
import asyncio
import logging

# Import models so their class definitions run and register on Base.metadata
from mcp.db import models  # noqa: F401

from mcp.db.session import create_tables, Base

async def main():
    logging.basicConfig(level=logging.INFO)
    logging.info("Registered tables BEFORE create: %s", list(Base.metadata.tables.keys()))
    await create_tables()
    logging.info("Registered tables AFTER create: %s", list(Base.metadata.tables.keys()))
    print(" Database initialized.")

if __name__ == "__main__":
    asyncio.run(main())
