from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from typing import List, Optional
from app.database import get_db
from app.models import Request, User, RequestStatus
from app.schemas import RequestCreate, RequestUpdate, RequestResponse
from app.auth import get_current_user, require_manager
from app.ai_service import ai_service
from app.websocket import manager

router = APIRouter(prefix="/api/requests", tags=["Requests"])

@router.get("", response_model=List[RequestResponse])
async def get_requests(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status_filter: Optional[RequestStatus] = None,
    category_filter: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Use selectinload to eagerly load relationships
    query = select(Request).options(
        selectinload(Request.guest),
        selectinload(Request.room)
    )
    
    if status_filter:
        query = query.filter(Request.status == status_filter)
    
    if category_filter:
        query = query.filter(Request.category == category_filter)
    
    query = query.order_by(desc(Request.created_at)).offset(skip).limit(limit)
    result = await db.execute(query)
    requests = result.scalars().all()
    return requests

@router.post("", response_model=RequestResponse, status_code=status.HTTP_201_CREATED)
async def create_request(
    request_data: RequestCreate,
    db: AsyncSession = Depends(get_db)
):
    category = await ai_service.categorize_request(request_data.description)
    
    new_request = Request(
        guest_id=request_data.guest_id,
        room_id=request_data.room_id,
        description=request_data.description,
        category=category,
        status=RequestStatus.PENDING
    )
    
    db.add(new_request)
    await db.commit()
    await db.refresh(new_request)
    
    # Eagerly load relationships before serialization
    result = await db.execute(
        select(Request)
        .options(selectinload(Request.guest), selectinload(Request.room))
        .filter(Request.id == new_request.id)
    )
    loaded_request = result.scalar_one()
    
    await manager.broadcast({
        "type": "new_request",
        "data": RequestResponse.model_validate(loaded_request).model_dump(mode='json')
    })
    
    return loaded_request

@router.patch("/{request_id}", response_model=RequestResponse)
async def update_request_status(
    request_id: int,
    update_data: RequestUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    # Eagerly load relationships
    result = await db.execute(
        select(Request)
        .options(selectinload(Request.guest), selectinload(Request.room))
        .filter(Request.id == request_id)
    )
    request_obj = result.scalar_one_or_none()
    
    if not request_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Request not found"
        )
    
    request_obj.status = update_data.status
    await db.commit()
    
    # Reload with relationships after update
    result = await db.execute(
        select(Request)
        .options(selectinload(Request.guest), selectinload(Request.room))
        .filter(Request.id == request_id)
    )
    updated_request = result.scalar_one()
    
    await manager.broadcast({
        "type": "request_updated",
        "data": RequestResponse.model_validate(updated_request).model_dump(mode='json')
    })
    
    return updated_request
