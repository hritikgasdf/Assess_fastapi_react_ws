from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional
from app.models import UserRole, RequestStatus, SentimentType

class UserBase(BaseModel):
    email: EmailStr
    full_name: str

class UserCreate(UserBase):
    password: str
    role: Optional[UserRole] = UserRole.STAFF

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(UserBase):
    id: int
    role: UserRole
    created_at: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

class GuestBase(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: Optional[str] = None

class GuestResponse(GuestBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class RoomBase(BaseModel):
    room_number: str
    room_type: str
    floor: int

class RoomResponse(RoomBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class RequestBase(BaseModel):
    description: str

class RequestCreate(RequestBase):
    guest_id: int
    room_id: int

class RequestUpdate(BaseModel):
    status: RequestStatus

class RequestResponse(RequestBase):
    id: int
    guest_id: int
    room_id: int
    category: str
    status: RequestStatus
    created_at: datetime
    updated_at: datetime
    guest: Optional[GuestResponse] = None
    room: Optional[RoomResponse] = None

    class Config:
        from_attributes = True

class FeedbackBase(BaseModel):
    message: str

class FeedbackCreate(FeedbackBase):
    guest_id: int
    room_id: int

class FeedbackResponse(FeedbackBase):
    id: int
    guest_id: int
    room_id: int
    sentiment: SentimentType
    smart_response: Optional[str] = None
    created_at: datetime
    guest: Optional[GuestResponse] = None
    room: Optional[RoomResponse] = None

    class Config:
        from_attributes = True

class SmartResponseResponse(BaseModel):
    feedback_id: int
    smart_response: str
