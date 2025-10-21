from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from app.config import settings

# Convert PostgreSQL URL to async version
DATABASE_URL = settings.DATABASE_URL
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
elif DATABASE_URL.startswith("sqlite:"):
    # For SQLite, use aiosqlite
    DATABASE_URL = DATABASE_URL.replace("sqlite:", "sqlite+aiosqlite:")

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    pool_pre_ping=True,  # Test connections before using them
    pool_size=5,  # Reduced for Supabase connection limits
    max_overflow=10,  # Reduced overflow connections
    pool_recycle=300,  # Recycle connections after 5 minutes (Supabase pooler timeout)
    pool_timeout=10,  # Reduced timeout to fail faster
    connect_args={
        "timeout": 10,  # Connection timeout in seconds
        "command_timeout": 10,  # Command execution timeout
    }
)
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)
Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
