from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import uuid

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    name = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    api_key = Column(String(255), unique=True, default=lambda: str(uuid.uuid4()))
    
    # Relationships
    bots = relationship("Bot", back_populates="owner", cascade="all, delete-orphan")

class Bot(Base):
    __tablename__ = "bots"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, default="")
    welcome_message = Column(String(500), default="Hello! How can I help you today?")
    primary_color = Column(String(7), default="#007bff")
    secondary_color = Column(String(7), default="#6c757d")
    position = Column(String(20), default="bottom-right")
    is_active = Column(Boolean, default=True)
    theme = Column(String(50), default="light")
    language = Column(String(10), default="en")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = Column(Integer, ForeignKey("users.id"))
    
    # Analytics
    total_conversations = Column(Integer, default=0)
    total_queries = Column(Integer, default=0)
    satisfaction_score = Column(Float, default=0.0)
    
    # Relationships
    owner = relationship("User", back_populates="bots")
    faqs = relationship("FAQ", back_populates="bot", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="bot", cascade="all, delete-orphan")

class FAQ(Base):
    __tablename__ = "faqs"
    
    id = Column(Integer, primary_key=True)
    question = Column(String(500), nullable=False)
    answer = Column(Text, nullable=False)
    category = Column(String(100), default="General")
    priority = Column(Integer, default=0)  # Higher = more important
    times_asked = Column(Integer, default=0)
    helpful_count = Column(Integer, default=0)
    not_helpful_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    bot_id = Column(Integer, ForeignKey("bots.id"))
    
    # Relationships
    bot = relationship("Bot", back_populates="faqs")

class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True)
    session_id = Column(String(255), nullable=False)
    user_message = Column(Text)
    bot_response = Column(Text)
    was_helpful = Column(Boolean, default=None)
    response_time_ms = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    bot_id = Column(Integer, ForeignKey("bots.id"))
    
    # Relationships
    bot = relationship("Bot", back_populates="conversations")

# Create database
engine = create_engine("sqlite:///chatbot_builder.db", connect_args={"check_same_thread": False})
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine)