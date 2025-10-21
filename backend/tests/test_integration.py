"""
Integration tests for complex workflows and multi-step processes.
Tests the complete Smart Response workflow, async state management, and error handling.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.main import app
from app.database import Base, get_db
from app.models import User, Guest, Room, Request, Feedback, UserRole
from app.auth import create_access_token, get_password_hash


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
            message="Room was cold and uncomfortable",
            sentiment="Negative"
        )
        db_session.add(feedback)
        await db_session.commit()
        await db_session.refresh(feedback)
        return feedback


@pytest.mark.asyncio
async def test_complete_feedback_workflow(manager_user, feedback_item):
    """
    Test complete feedback processing workflow:
    1. Feedback exists with comment
    2. Manager requests smart response
    3. AI analyzes sentiment
    4. AI generates response
    5. Response is saved
    """
    token = create_access_token({"sub": manager_user.email, "role": manager_user.role})
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Step 1: Verify feedback exists
        response = await client.get(
            "/api/feedback",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        feedbacks = response.json()
        assert len(feedbacks) > 0
        feedback = feedbacks[0]
        assert feedback["message"] == "Room was cold and uncomfortable"
        
        # Step 2: Generate smart response (triggers AI workflow)
        response = await client.post(
            f"/api/feedback/{feedback_item.id}/generate-response",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        result = response.json()
        
        # Step 3: Verify AI workflow completed
        assert "smart_response" in result
        assert result["smart_response"] is not None
        assert len(result["smart_response"]) > 0
        
        # Step 4: Verify feedback_id is included
        assert "feedback_id" in result
        assert result["feedback_id"] == feedback_item.id
        
        # Step 5: Verify response contains relevant content
        smart_response = result["smart_response"].lower()
        # Response should be an apology/acknowledgment for negative feedback
        assert any(word in smart_response for word in ["sorry", "apologize", "regret", "unfortunate", "concern"])


@pytest.mark.asyncio
async def test_smart_response_requires_manager_role(staff_user, feedback_item):
    """
    Test that Smart Response generation enforces manager-only access
    """
    token = create_access_token({"sub": staff_user.email, "role": staff_user.role})
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/feedback/{feedback_item.id}/generate-response",
            headers={"Authorization": f"Bearer {token}"}
        )
        # Staff should be forbidden from generating smart responses
        assert response.status_code == 403
        assert "Manager role required" in response.json()["detail"]


@pytest.mark.asyncio
async def test_request_status_update_workflow(manager_user, staff_user, request_item):
    """
    Test request status update workflow with role enforcement:
    1. Manager can update status
    2. Staff cannot update status
    3. Status changes are persisted
    """
    manager_token = create_access_token({"sub": manager_user.email, "role": manager_user.role})
    staff_token = create_access_token({"sub": staff_user.email, "role": staff_user.role})
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Step 1: Staff tries to update (should fail)
        response = await client.patch(
            f"/api/requests/{request_item.id}",
            json={"status": "In Progress"},
            headers={"Authorization": f"Bearer {staff_token}"}
        )
        assert response.status_code == 403
        
        # Step 2: Manager updates status (should succeed)
        response = await client.patch(
            f"/api/requests/{request_item.id}",
            json={"status": "In Progress"},
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        assert response.status_code == 200
        updated_request = response.json()
        assert updated_request["status"] == "In Progress"
        
        # Step 3: Verify status persisted
        response = await client.get(
            "/api/requests",
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        assert response.status_code == 200
        requests = response.json()
        found = False
        for req in requests:
            if req["id"] == request_item.id:
                assert req["status"] == "In Progress"
                found = True
                break
        assert found, "Updated request not found in list"


@pytest.mark.asyncio
async def test_async_state_updates_dont_block(manager_user, feedback_item):
    """
    Test that AI operations don't block other async operations.
    Simulates concurrent requests to ensure no blocking.
    """
    import asyncio
    
    token = create_access_token({"sub": manager_user.email, "role": manager_user.role})
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create multiple concurrent requests
        tasks = []
        
        # Task 1: Generate smart response (AI operation)
        tasks.append(
            client.post(
                f"/api/feedback/{feedback_item.id}/generate-response",
                headers={"Authorization": f"Bearer {token}"}
            )
        )
        
        # Task 2: Get feedback list (database operation)
        tasks.append(
            client.get(
                "/api/feedback",
                headers={"Authorization": f"Bearer {token}"}
            )
        )
        
        # Task 3: Get requests list (database operation)
        tasks.append(
            client.get(
                "/api/requests",
                headers={"Authorization": f"Bearer {token}"}
            )
        )
        
        # Execute all tasks concurrently
        start_time = asyncio.get_event_loop().time()
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        elapsed_time = asyncio.get_event_loop().time() - start_time
        
        # Verify all requests completed
        assert len(responses) == 3
        for response in responses:
            assert not isinstance(response, Exception), f"Request failed: {response}"
            assert response.status_code == 200
        
        # If operations were blocking, this would take much longer
        # With async operations, should complete quickly (< 3 seconds)
        assert elapsed_time < 3.0, f"Operations took too long: {elapsed_time}s (possible blocking)"


@pytest.mark.asyncio
async def test_workflow_error_handling(manager_user):
    """
    Test error handling in multi-step workflows:
    1. Invalid feedback ID
    2. Missing required data
    """
    token = create_access_token({"sub": manager_user.email, "role": manager_user.role})
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Test 1: Invalid feedback ID
        response = await client.post(
            "/api/feedback/99999/generate-response",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
        
        # Test 2: Invalid request ID for update
        response = await client.patch(
            "/api/requests/99999",
            json={"status": "Completed"},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_sentiment_analysis_integration(guest, room):
    """
    Test that sentiment analysis is properly integrated:
    1. Creates feedback with different sentiments
    2. Verifies sentiment is stored
    """
    async with TestingSessionLocal() as db_session:
        # Create feedback with clearly positive sentiment
        positive_feedback = Feedback(
            guest_id=guest.id,
            room_id=room.id,
            message="Excellent service! Amazing staff and wonderful experience!",
            sentiment="Positive"
        )
        db_session.add(positive_feedback)
        
        # Create feedback with clearly negative sentiment
        negative_feedback = Feedback(
            guest_id=guest.id,
            room_id=room.id,
            message="Terrible experience. Room was dirty and staff was rude.",
            sentiment="Negative"
        )
        db_session.add(negative_feedback)
        
        await db_session.commit()
        await db_session.refresh(positive_feedback)
        await db_session.refresh(negative_feedback)
        
        # Verify feedback was created
        assert positive_feedback.id is not None
        assert negative_feedback.id is not None
        
        # Verify sentiment is stored correctly
        assert positive_feedback.sentiment == "Positive"
        assert negative_feedback.sentiment == "Negative"


@pytest.mark.asyncio
async def test_authentication_flow_integration(setup_database):
    """
    Test complete authentication flow:
    1. Register user
    2. Login
    3. Access protected endpoint
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Step 1: Register
        response = await client.post(
            "/api/auth/register",
            json={
                "email": "newuser@hotel.com",
                "password": "password123",
                "full_name": "New User",
                "role": "Staff"
            }
        )
        assert response.status_code == 201
        user_data = response.json()
        assert user_data["email"] == "newuser@hotel.com"
        
        # Step 2: Login
        response = await client.post(
            "/api/auth/login",
            json={
                "email": "newuser@hotel.com",
                "password": "password123"
            }
        )
        assert response.status_code == 200
        login_data = response.json()
        assert "access_token" in login_data
        token = login_data["access_token"]
        
        # Step 3: Access protected endpoint
        response = await client.get(
            "/api/requests",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        # New user should see empty list
        assert isinstance(response.json(), list)
