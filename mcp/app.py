# mcp/app.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mcp.routes.llm_routes import get_llm_service
from mcp.routes import llm_routes 
from mcp.routes.reviews import router as reviews_router

app = FastAPI(title="HTTP Server for Review Processing")

# CORS setup
origins = [
    "https://expertiza.ncsu.edu",  # production
    "http://localhost:3000",        # local dev
    "http://152.7.178.226:8080/"  # staging server
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(llm_routes.router, prefix="/api/review")
app.include_router(reviews_router, prefix="/api/v1")



@app.on_event("shutdown")
async def close_llm_service():
    svc = get_llm_service()
    await svc.close()