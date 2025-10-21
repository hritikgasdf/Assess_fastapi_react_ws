"""
Security-focused tests for the application.
Tests SQL injection prevention, XSS prevention, token security, and authorization boundaries.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.main import app
from app.database import Base, get_db
from app.models import User, Guest, Room, Request, Feedback, UserRole
from app.auth import create_access_token, get_password_hash
from datetime import datetime, timedelta
import jwt
from app.config import settings


# Test database setup - use SAME database as test_api.py for consistency
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

engine = create_async_engine(TEST_DATABASE_URL, echo=False, connect_args={"check_same_thread": False})
TestingSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="function")
async def setup_database():
    """Setup test database for each test"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def manager_user(setup_database):
    """Create a manager user"""
    async with TestingSessionLocal() as db_session:
        user = User(
            email="manager@hotel.com",
            full_name="Manager User",
            hashed_password=get_password_hash("manager123"),
            role=UserRole.MANAGER
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return user


@pytest.fixture
async def staff_user(setup_database):
    """Create a staff user"""
    async with TestingSessionLocal() as db_session:
        user = User(
            email="staff@hotel.com",
            full_name="Staff User",
            hashed_password=get_password_hash("staff123"),
            role=UserRole.STAFF
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return user


@pytest.fixture
async def guest(setup_database):
    """Create a guest"""
    async with TestingSessionLocal() as db_session:
        guest = Guest(
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            phone="1234567890"
        )
        db_session.add(guest)
        await db_session.commit()
        await db_session.refresh(guest)
        return guest


@pytest.fixture
async def room(setup_database):
    """Create a room"""
    async with TestingSessionLocal() as db_session:
        room = Room(
            room_number="101",
            room_type="Standard",
            floor=1
        )
        db_session.add(room)
        await db_session.commit()
        await db_session.refresh(room)
        return room


@pytest.fixture
async def request_item(setup_database, guest, room):
    """Create a request"""
    async with TestingSessionLocal() as db_session:
        request = Request(
            guest_id=guest.id,
            room_id=room.id,
            category="Housekeeping",
            description="Need fresh towels",
            status="Pending"
        )
        db_session.add(request)
        await db_session.commit()
        await db_session.refresh(request)
        return request


@pytest.fixture
async def feedback_item(setup_database, guest, room):
    """Create feedback with NEGATIVE sentiment for smart response testing"""
    async with TestingSessionLocal() as db_session:
        feedback = Feedback(
            guest_id=guest.id,
            room_id=room.id,
            message="Terrible service and dirty room",
            sentiment="Negative"
        )
        db_session.add(feedback)
        await db_session.commit()
        await db_session.refresh(feedback)
        return feedback


@pytest.mark.asyncio
async def test_sql_injection_prevention(manager_user):
    """
    Test that SQL injection attempts are prevented.
    Attempts common SQL injection patterns in various inputs.
    """
    token = create_access_token({"sub": manager_user.email, "role": manager_user.role})
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Test 1: SQL injection in registration email
        sql_injection_emails = [
            "admin'--",
            "admin' OR '1'='1",
            "'; DROP TABLE users; --",
            "admin'; DELETE FROM users WHERE '1'='1",
        ]
        
        for malicious_email in sql_injection_emails:
            response = await client.post(
                "/api/auth/register",
                json={
                    "email": malicious_email,
                    "password": "password123",
                    "full_name": "Test User",
                    "role": "Staff"
                }
            )
            # Should either validate email format or handle safely
            # Should NOT cause SQL injection or server error
            assert response.status_code in [201, 400, 422], f"Unexpected status for {malicious_email}"
        
        # Test 2: SQL injection in request description
        response = await client.post(
            "/api/requests",
            json={
                "guest_id": 1,
                "request_type": "maintenance",
                "description": "'; DROP TABLE requests; --",
                "priority": "high"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        # Should handle safely (either create or validate)
        assert response.status_code in [200, 201, 400, 404, 422]
        
        # Test 3: Verify requests table still exists
        response = await client.get(
            "/api/requests",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        # If we get here, table wasn't dropped


@pytest.mark.asyncio
async def test_xss_prevention(manager_user, guest, room):
    """
    Test that XSS attacks are prevented or sanitized.
    Tests common XSS patterns in user inputs.
    """
    token = create_access_token({"sub": manager_user.email, "role": manager_user.role})
    
    xss_payloads = [
        "<script>alert('XSS')</script>",
        "<img src=x onerror=alert('XSS')>",
        "javascript:alert('XSS')",
        "<svg onload=alert('XSS')>",
    ]
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for payload in xss_payloads:
            # Test XSS in request description
            response = await client.post(
                "/api/requests",
                json={
                    "guest_id": guest.id,
                    "room_id": room.id,
                    "category": "General",
                    "description": payload,
                    "status": "Pending"
                },
                headers={"Authorization": f"Bearer {token}"}
            )
            
            # Should accept (stored XSS prevention is frontend responsibility)
            # OR validate and reject
            assert response.status_code in [200, 201, 400, 422]
            
            if response.status_code in [200, 201]:
                # If accepted, verify it's stored (will be sanitized on frontend)
                request_data = response.json()
                assert "description" in request_data
                # Backend stores as-is; frontend should sanitize before rendering


@pytest.mark.asyncio
async def test_token_expiration(setup_database):
    """
    Test that expired tokens are rejected.
    """
    # Create an expired token
    expired_time = datetime.utcnow() - timedelta(hours=1)
    expired_token_data = {
        "sub": "test@hotel.com",
        "role": "manager",
        "exp": expired_time
    }
    expired_token = jwt.encode(expired_token_data, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/requests",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        # Should reject expired token
        assert response.status_code == 401
        assert "credentials" in response.json()["detail"].lower() or "expired" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_invalid_token_format(setup_database):
    """
    Test that invalid token formats are rejected.
    """
    invalid_tokens = [
        "invalid.token.format",
        "Bearer not_a_jwt_token",
        "malformed_token",
        "",
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid",
    ]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for invalid_token in invalid_tokens:
            response = await client.get(
                "/api/requests",
                headers={"Authorization": f"Bearer {invalid_token}"}
            )
            # HTTPBearer returns 403 for malformed tokens (standard FastAPI behavior)
            assert response.status_code in [401, 403]
@pytest.mark.asyncio
async def test_authorization_headers(manager_user):
    """
    Test various authorization header formats.
    """
    valid_token = create_access_token({"sub": manager_user.email, "role": manager_user.role})
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Test 1: Missing Authorization header (HTTPBearer returns 403)
        response = await client.get("/api/requests")
        assert response.status_code == 403
        
        # Test 2: Valid Bearer token
        response = await client.get(
            "/api/requests",
            headers={"Authorization": f"Bearer {valid_token}"}
        )
        assert response.status_code == 200
        
        # Test 3: Token without "Bearer" prefix (should fail with 403 from HTTPBearer)
        response = await client.get(
            "/api/requests",
            headers={"Authorization": valid_token}
        )
        assert response.status_code == 403
        
        # Test 4: Wrong authentication scheme (HTTPBearer rejects with 403)
        response = await client.get(
            "/api/requests",
            headers={"Authorization": f"Basic {valid_token}"}
        )
        assert response.status_code == 403


@pytest.mark.asyncio
async def test_role_boundary_checks(manager_user, staff_user, request_item, feedback_item):
    """
    Test that role boundaries are properly enforced.
    Staff should not be able to perform manager-only operations.
    """
    manager_token = create_access_token({"sub": manager_user.email, "role": manager_user.role})
    staff_token = create_access_token({"sub": staff_user.email, "role": staff_user.role})
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Test 1: Staff cannot update request status
        response = await client.patch(
            f"/api/requests/{request_item.id}",
            json={"status": "Completed"},
            headers={"Authorization": f"Bearer {staff_token}"}
        )
        assert response.status_code == 403
        assert "Manager role required" in response.json()["detail"]
        
        # Test 2: Manager CAN update request status
        response = await client.patch(
            f"/api/requests/{request_item.id}",
            json={"status": "Completed"},
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        assert response.status_code == 200
        
        # Test 3: Staff cannot generate smart response
        response = await client.post(
            f"/api/feedback/{feedback_item.id}/generate-response",
            headers={"Authorization": f"Bearer {staff_token}"}
        )
        assert response.status_code == 403
        
        # Test 4: Manager CAN generate smart response
        response = await client.post(
            f"/api/feedback/{feedback_item.id}/generate-response",
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        assert response.status_code == 200
        
        # Test 5: Both roles can read data
        for token in [manager_token, staff_token]:
            response = await client.get(
                "/api/requests",
                headers={"Authorization": f"Bearer {token}"}
            )
            assert response.status_code == 200
            
            response = await client.get(
                "/api/feedback",
                headers={"Authorization": f"Bearer {token}"}
            )
            assert response.status_code == 200


@pytest.mark.asyncio
async def test_password_security(setup_database):
    """
    Test that passwords are properly hashed and not exposed.
    """
    # Create a user with known password
    plain_password = "supersecret123"
    hashed = get_password_hash(plain_password)
    
    async with TestingSessionLocal() as db_session:
        user = User(
            email="security@hotel.com",
            full_name="Security User",
            hashed_password=hashed,
            role=UserRole.STAFF
        )
        db_session.add(user)
        await db_session.commit()
    
    # Test 1: Hashed password is not the same as plain password
    assert hashed != plain_password
    
    # Test 2: Hash is not easily reversible (one-way)
    assert len(hashed) > 50  # bcrypt hashes are long
    assert hashed.startswith("$2b$")  # bcrypt format
    
    # Test 3: API doesn't expose hashed password
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/auth/register",
            json={
                "email": "another@hotel.com",
                "password": "password123",
                "full_name": "Another User",
                "role": "Staff"
            }
        )
        assert response.status_code == 201
        user_data = response.json()
        
        # Password fields should not be in response
        assert "password" not in user_data
        assert "hashed_password" not in user_data
        
        # Only safe fields should be exposed
        assert "email" in user_data
        assert "role" in user_data
        assert "id" in user_data
