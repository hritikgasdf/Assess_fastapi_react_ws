import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.main import app
from app.database import Base, get_db
from app.models import User, Guest, Room, UserRole
from app.auth import get_password_hash

# Use SQLite for testing with async support
SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./test.db"
engine = create_async_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="function")
async def test_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
async def client(test_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

@pytest.fixture
async def test_user(test_db):
    async with TestingSessionLocal() as db:
        user = User(
            email="test@hotel.com",
            full_name="Test User",
            hashed_password=get_password_hash("test123"),
            role=UserRole.STAFF
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

@pytest.fixture
async def test_manager(test_db):
    async with TestingSessionLocal() as db:
        manager = User(
            email="manager@hotel.com",
            full_name="Test Manager",
            hashed_password=get_password_hash("manager123"),
            role=UserRole.MANAGER
        )
        db.add(manager)
        await db.commit()
        await db.refresh(manager)
        return manager

@pytest.fixture
async def test_guest(test_db):
    async with TestingSessionLocal() as db:
        guest = Guest(
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            phone="+1234567890"
        )
        db.add(guest)
        await db.commit()
        await db.refresh(guest)
        return guest

@pytest.fixture
async def test_room(test_db):
    async with TestingSessionLocal() as db:
        room = Room(
            room_number="101",
            room_type="Standard",
            floor=1
        )
        db.add(room)
        await db.commit()
        await db.refresh(room)
        return room

@pytest.fixture
async def auth_token(client, test_user):
    response = await client.post(
        "/api/auth/login",
        json={"email": "test@hotel.com", "password": "test123"}
    )
    return response.json()["access_token"]

@pytest.fixture
async def manager_token(client, test_manager):
    response = await client.post(
        "/api/auth/login",
        json={"email": "manager@hotel.com", "password": "manager123"}
    )
    return response.json()["access_token"]

async def test_register_user(client):
    response = await client.post(
        "/api/auth/register",
        json={
            "email": "newuser@hotel.com",
            "full_name": "New User",
            "password": "newpass123"
        }
    )
    assert response.status_code == 201
    assert response.json()["email"] == "newuser@hotel.com"

async def test_register_duplicate_email(client, test_user):
    response = await client.post(
        "/api/auth/register",
        json={
            "email": "test@hotel.com",
            "full_name": "Duplicate User",
            "password": "pass123"
        }
    )
    assert response.status_code == 400

async def test_login_success(client, test_user):
    response = await client.post(
        "/api/auth/login",
        json={"email": "test@hotel.com", "password": "test123"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()

async def test_login_wrong_password(client, test_user):
    response = await client.post(
        "/api/auth/login",
        json={"email": "test@hotel.com", "password": "wrongpass"}
    )
    assert response.status_code == 401

async def test_get_requests_authenticated(client, auth_token):
    response = await client.get(
        "/api/requests",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)

async def test_get_requests_unauthenticated(client):
    response = await client.get("/api/requests")
    assert response.status_code == 403

async def test_create_request(client, test_guest, test_room):
    response = await client.post(
        "/api/requests",
        json={
            "guest_id": test_guest.id,
            "room_id": test_room.id,
            "description": "Need extra towels"
        }
    )
    assert response.status_code == 201
    assert response.json()["description"] == "Need extra towels"
    assert "category" in response.json()

async def test_update_request_as_manager(client, manager_token, test_guest, test_room):
    create_response = await client.post(
        "/api/requests",
        json={
            "guest_id": test_guest.id,
            "room_id": test_room.id,
            "description": "Need room service"
        }
    )
    request_id = create_response.json()["id"]
    
    update_response = await client.patch(
        f"/api/requests/{request_id}",
        json={"status": "Completed"},
        headers={"Authorization": f"Bearer {manager_token}"}
    )
    assert update_response.status_code == 200
    assert update_response.json()["status"] == "Completed"

async def test_update_request_as_staff_forbidden(client, auth_token, test_guest, test_room):
    create_response = await client.post(
        "/api/requests",
        json={
            "guest_id": test_guest.id,
            "room_id": test_room.id,
            "description": "Need maintenance"
        }
    )
    request_id = create_response.json()["id"]
    
    update_response = await client.patch(
        f"/api/requests/{request_id}",
        json={"status": "Completed"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert update_response.status_code == 403

async def test_get_feedback_authenticated(client, auth_token):
    response = await client.get(
        "/api/feedback",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)

async def test_create_feedback(client, test_guest, test_room):
    response = await client.post(
        "/api/feedback",
        json={
            "guest_id": test_guest.id,
            "room_id": test_room.id,
            "message": "Great experience, loved the stay!"
        }
    )
    assert response.status_code == 201
    assert response.json()["message"] == "Great experience, loved the stay!"
    assert "sentiment" in response.json()

async def test_generate_smart_response_manager(client, manager_token, test_guest, test_room):
    feedback_response = await client.post(
        "/api/feedback",
        json={
            "guest_id": test_guest.id,
            "room_id": test_room.id,
            "message": "Terrible service, very disappointed and unhappy"
        }
    )
    feedback_id = feedback_response.json()["id"]
    
    response = await client.post(
        f"/api/feedback/{feedback_id}/generate-response",
        headers={"Authorization": f"Bearer {manager_token}"}
    )
    assert response.status_code == 200
    assert "smart_response" in response.json()

async def test_generate_smart_response_staff_forbidden(client, auth_token, test_guest, test_room):
    feedback_response = await client.post(
        "/api/feedback",
        json={
            "guest_id": test_guest.id,
            "room_id": test_room.id,
            "message": "Bad experience"
        }
    )
    feedback_id = feedback_response.json()["id"]
    
    response = await client.post(
        f"/api/feedback/{feedback_id}/generate-response",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 403
