from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.database import engine, Base
from app.routes import auth, requests, feedback, websocket_routes
from app.logger import setup_logger

logger = setup_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise
    
    yield
    
    # Cleanup on shutdown - dispose engine gracefully
    try:
        await engine.dispose()
        logger.info("Database engine disposed")
    except Exception as e:
        logger.warning(f"Error disposing engine: {e}")

app = FastAPI(title="Hotel Operations Dashboard API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(requests.router)
app.include_router(feedback.router)
app.include_router(websocket_routes.router)

@app.get("/")
def read_root():
    return {"message": "Hotel Operations Dashboard API"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}
