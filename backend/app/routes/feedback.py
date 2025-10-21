from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from typing import List, Optional
from app.database import get_db
from app.models import Feedback, User, SentimentType
from app.schemas import FeedbackCreate, FeedbackResponse, SmartResponseResponse
from app.auth import get_current_user, require_manager
from app.ai_service import ai_service
from app.websocket import manager

router = APIRouter(prefix="/api/feedback", tags=["Feedback"])

@router.get("", response_model=List[FeedbackResponse])
async def get_feedback(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    sentiment_filter: Optional[SentimentType] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = select(Feedback).options(
        selectinload(Feedback.guest),
        selectinload(Feedback.room)
    )
    
    if sentiment_filter:
        query = query.filter(Feedback.sentiment == sentiment_filter)
    
    query = query.order_by(desc(Feedback.created_at)).offset(skip).limit(limit)
    result = await db.execute(query)
    feedbacks = result.scalars().all()
    return feedbacks

@router.post("", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
async def create_feedback(
    feedback_data: FeedbackCreate,
    db: AsyncSession = Depends(get_db)
):
    sentiment = await ai_service.analyze_sentiment(feedback_data.message)
    
    new_feedback = Feedback(
        guest_id=feedback_data.guest_id,
        room_id=feedback_data.room_id,
        message=feedback_data.message,
        sentiment=sentiment
    )
    
    db.add(new_feedback)
    await db.commit()
    await db.refresh(new_feedback)
    
    result = await db.execute(
        select(Feedback)
        .options(selectinload(Feedback.guest), selectinload(Feedback.room))
        .filter(Feedback.id == new_feedback.id)
    )
    loaded_feedback = result.scalar_one()
    
    await manager.broadcast({
        "type": "new_feedback",
        "data": FeedbackResponse.model_validate(loaded_feedback).model_dump(mode='json')
    })
    
    return loaded_feedback

@router.post("/{feedback_id}/generate-response", response_model=SmartResponseResponse)
async def generate_smart_response(
    feedback_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    result = await db.execute(
        select(Feedback)
        .options(selectinload(Feedback.guest), selectinload(Feedback.room))
        .filter(Feedback.id == feedback_id)
    )
    feedback = result.scalar_one_or_none()
    
    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found"
        )
    
    if feedback.sentiment != SentimentType.NEGATIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Smart response generation is only available for negative feedback"
        )
    
    smart_response = await ai_service.generate_smart_response(feedback.message)
    
    feedback.smart_response = smart_response
    await db.commit()
    
    # Reload with relationships after update
    result = await db.execute(
        select(Feedback)
        .options(selectinload(Feedback.guest), selectinload(Feedback.room))
        .filter(Feedback.id == feedback_id)
    )
    updated_feedback = result.scalar_one()
    
    await manager.broadcast({
        "type": "feedback_updated",
        "data": FeedbackResponse.model_validate(updated_feedback).model_dump(mode='json')
    })
    
    return SmartResponseResponse(
        feedback_id=updated_feedback.id,
        smart_response=smart_response
    )
