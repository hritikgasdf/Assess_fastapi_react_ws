import asyncio
import traceback
from app.database import engine
from sqlalchemy import text

async def test_connection():
    print("Testing PostgreSQL connection with optimized settings...")
    print("Connection pool: size=5, max_overflow=10, timeout=10s")
    try:
        async with engine.begin() as conn:
            result = await conn.execute(text('SELECT 1'))
            print("✅ PostgreSQL connection successful!")
    except Exception as e:
        print(f"❌ Connection failed:")
        traceback.print_exc()
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(test_connection())
