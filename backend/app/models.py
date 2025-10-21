from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SQLEnum, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.database import Base

class UserRole(str, enum.Enum):
    STAFF = "Staff"
    MANAGER = "Manager"

class RequestStatus(str, enum.Enum):
    PENDING = "Pending"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"

class SentimentType(str, enum.Enum):
    POSITIVE = "Positive"
    NEGATIVE = "Negative"
    NEUTRAL = "Neutral"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.STAFF, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Guest(Base):
    __tablename__ = "guests"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    requests = relationship("Request", back_populates="guest")
    feedbacks = relationship("Feedback", back_populates="guest")

class Room(Base):
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True, index=True)
    room_number = Column(String, unique=True, nullable=False, index=True)
    room_type = Column(String, nullable=False)
    floor = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    requests = relationship("Request", back_populates="room")
    feedbacks = relationship("Feedback", back_populates="room")

class Request(Base):
    __tablename__ = "requests"

    id = Column(Integer, primary_key=True, index=True)
    guest_id = Column(Integer, ForeignKey("guests.id", ondelete="CASCADE"), nullable=False)
    room_id = Column(Integer, ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False)
    category = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    status = Column(SQLEnum(RequestStatus), default=RequestStatus.PENDING, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    guest = relationship("Guest", back_populates="requests")
    room = relationship("Room", back_populates="requests")

class Feedback(Base):
    __tablename__ = "feedbacks"

    id = Column(Integer, primary_key=True, index=True)
    guest_id = Column(Integer, ForeignKey("guests.id", ondelete="CASCADE"), nullable=False)
    room_id = Column(Integer, ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False)
    message = Column(Text, nullable=False)
    sentiment = Column(SQLEnum(SentimentType), nullable=False)
    smart_response = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    guest = relationship("Guest", back_populates="feedbacks")
    room = relationship("Room", back_populates="feedbacks")
