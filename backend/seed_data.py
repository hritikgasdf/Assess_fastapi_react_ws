import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.database import Base
from app.models import User, Guest, Room, Request, Feedback, UserRole, RequestStatus, SentimentType
from app.auth import get_password_hash
from app.logger import setup_logger
from datetime import datetime, timedelta
import os

logger = setup_logger(__name__)

async def seed_database():
    """
    Async database seeding function that creates tables and populates initial data.
    Designed to work with Docker and async SQLAlchemy.
    """
    # Get database URL from environment
    database_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/hotel_ops")
    
    # Convert to async URL
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")
    
    logger.info(f"Connecting to database for seeding...")
    
    # Create async engine for seeding
    engine = create_async_engine(
        database_url,
        echo=False,
        pool_pre_ping=True,
    )
    
    # Create session maker
    async_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    try:
        # Create all tables
        logger.info("Creating database tables...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Database tables created successfully")
        
        # Check if database is already seeded
        async with async_session() as db:
            result = await db.execute(select(User).limit(1))
            existing_user = result.scalar_one_or_none()
            
            if existing_user:
                logger.info("⚠️  Database already seeded, skipping...")
                return
            
            # Seed users
            logger.info("Creating users...")
            users = [
                User(
                    email="manager@hotel.com",
                    full_name="John Manager",
                    hashed_password=get_password_hash("manager123"),
                    role=UserRole.MANAGER
                ),
                User(
                    email="staff@hotel.com",
                    full_name="Jane Staff",
                    hashed_password=get_password_hash("staff123"),
                    role=UserRole.STAFF
                ),
                User(
                    email="alice@hotel.com",
                    full_name="Alice Smith",
                    hashed_password=get_password_hash("alice123"),
                    role=UserRole.STAFF
                ),
            ]
            db.add_all(users)
            await db.commit()
            logger.info(f"✅ Created {len(users)} users")
            
            # Seed guests
            logger.info("Creating guests...")
            guests = [
                Guest(first_name="Emma", last_name="Watson", email="emma.watson@email.com", phone="+1234567890"),
                Guest(first_name="Michael", last_name="Johnson", email="michael.j@email.com", phone="+1234567891"),
                Guest(first_name="Sarah", last_name="Williams", email="sarah.w@email.com", phone="+1234567892"),
                Guest(first_name="David", last_name="Brown", email="david.b@email.com", phone="+1234567893"),
                Guest(first_name="Lisa", last_name="Anderson", email="lisa.a@email.com", phone="+1234567894"),
            ]
            db.add_all(guests)
            await db.commit()
            logger.info(f"✅ Created {len(guests)} guests")
            
            # Seed rooms
            logger.info("Creating rooms...")
            rooms = [
                Room(room_number="101", room_type="Standard", floor=1),
                Room(room_number="102", room_type="Standard", floor=1),
                Room(room_number="201", room_type="Deluxe", floor=2),
                Room(room_number="202", room_type="Deluxe", floor=2),
                Room(room_number="301", room_type="Suite", floor=3),
                Room(room_number="302", room_type="Suite", floor=3),
            ]
            db.add_all(rooms)
            await db.commit()
            logger.info(f"✅ Created {len(rooms)} rooms")
            
            # Seed requests
            logger.info("Creating requests...")
            requests = [
                Request(
                    guest_id=1,
                    room_id=1,
                    description="Need extra towels in the room",
                    category="Housekeeping",
                    status=RequestStatus.PENDING,
                    created_at=datetime.utcnow() - timedelta(hours=2)
                ),
                Request(
                    guest_id=2,
                    room_id=3,
                    description="Room service - would like dinner for two",
                    category="Room Service",
                    status=RequestStatus.IN_PROGRESS,
                    created_at=datetime.utcnow() - timedelta(hours=1)
                ),
                Request(
                    guest_id=3,
                    room_id=4,
                    description="The AC is not working properly",
                    category="Maintenance",
                    status=RequestStatus.PENDING,
                    created_at=datetime.utcnow() - timedelta(minutes=30)
                ),
                Request(
                    guest_id=4,
                    room_id=5,
                    description="Need help with wifi connection",
                    category="Technical Support",
                    status=RequestStatus.COMPLETED,
                    created_at=datetime.utcnow() - timedelta(hours=5)
                ),
                Request(
                    guest_id=5,
                    room_id=2,
                    description="Can I get fresh linens please?",
                    category="Housekeeping",
                    status=RequestStatus.PENDING,
                    created_at=datetime.utcnow() - timedelta(minutes=15)
                ),
            ]
            db.add_all(requests)
            await db.commit()
            logger.info(f"✅ Created {len(requests)} requests")
            
            # Seed feedbacks
            logger.info("Creating feedbacks...")
            feedbacks = [
                Feedback(
                    guest_id=1,
                    room_id=1,
                    message="Excellent stay! The staff was wonderful and the room was spotless. Will definitely come back!",
                    sentiment=SentimentType.POSITIVE,
                    created_at=datetime.utcnow() - timedelta(days=1)
                ),
                Feedback(
                    guest_id=2,
                    room_id=3,
                    message="Terrible experience. The room was dirty and the service was slow. Very disappointed.",
                    sentiment=SentimentType.NEGATIVE,
                    created_at=datetime.utcnow() - timedelta(hours=12)
                ),
                Feedback(
                    guest_id=3,
                    room_id=4,
                    message="The stay was okay. Nothing special but nothing terrible either.",
                    sentiment=SentimentType.NEUTRAL,
                    created_at=datetime.utcnow() - timedelta(hours=6)
                ),
                Feedback(
                    guest_id=4,
                    room_id=5,
                    message="Amazing hotel! Great location, fantastic amenities, and the staff went above and beyond.",
                    sentiment=SentimentType.POSITIVE,
                    created_at=datetime.utcnow() - timedelta(hours=3)
                ),
                Feedback(
                    guest_id=5,
                    room_id=2,
                    message="Very unhappy with the noise levels. Could barely sleep. This is unacceptable for the price.",
                    sentiment=SentimentType.NEGATIVE,
                    created_at=datetime.utcnow() - timedelta(hours=1)
                ),
            ]
            db.add_all(feedbacks)
            await db.commit()
            logger.info(f"✅ Created {len(feedbacks)} feedbacks")
            
            logger.info("=" * 60)
            logger.info("🎉 Database seeded successfully!")
            logger.info("=" * 60)
            logger.info("Test User Credentials:")
            logger.info("  Manager - Email: manager@hotel.com, Password: manager123")
            logger.info("  Staff   - Email: staff@hotel.com, Password: staff123")
            logger.info("  Staff   - Email: alice@hotel.com, Password: alice123")
            logger.info("=" * 60)
            
    except Exception as e:
        logger.error(f"❌ Error seeding database: {e}", exc_info=True)
        raise
    finally:
        await engine.dispose()
        logger.info("Database connection closed")

if __name__ == "__main__":
    asyncio.run(seed_database())
