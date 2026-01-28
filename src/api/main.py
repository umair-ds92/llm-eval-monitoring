from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.routes import evaluate, metrics, health
from src.common.logger import get_logger

logger = get_logger(__name__)

app = FastAPI(
    title="LLM Evaluation & Monitoring API",
    description="Production-grade evaluation system for LLM applications with cybersecurity focus",
    version="0.1.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)
app.include_router(evaluate.router)
app.include_router(metrics.router)

@app.on_event("startup")
async def startup_event():
    logger.info("LLM Eval API starting up...")
    # Initialize database if needed
    from src.storage.database import get_database
    db = get_database()
    db.create_tables()
    logger.info("API ready")

@app.get("/")
async def root():
    return {
        "message": "LLM Evaluation & Monitoring API",
        "docs": "/docs",
        "health": "/health"
    }