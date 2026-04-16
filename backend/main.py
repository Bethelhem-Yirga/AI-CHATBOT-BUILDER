from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import uuid
import os
import google.generativeai as genai
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(title="AI Chatbot Builder API")

# CORS
# CORS - Allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)
# ============ Database Setup ============
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    name = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    api_key = Column(String(255), unique=True, default=lambda: str(uuid.uuid4()))
    
    bots = relationship("Bot", back_populates="owner", cascade="all, delete-orphan")

class Bot(Base):
    __tablename__ = "bots"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, default="")
    welcome_message = Column(String(500), default="Hello! How can I help you today?")
    primary_color = Column(String(7), default="#007bff")
    position = Column(String(20), default="bottom-right")
    is_active = Column(Boolean, default=True)
    theme = Column(String(50), default="light")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = Column(Integer, ForeignKey("users.id"))
    
    total_conversations = Column(Integer, default=0)
    satisfaction_score = Column(Float, default=0.0)
    
    owner = relationship("User", back_populates="bots")
    faqs = relationship("FAQ", back_populates="bot", cascade="all, delete-orphan")

class FAQ(Base):
    __tablename__ = "faqs"
    
    id = Column(Integer, primary_key=True)
    question = Column(String(500), nullable=False)
    answer = Column(Text, nullable=False)
    category = Column(String(100), default="General")
    priority = Column(Integer, default=0)
    times_asked = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    bot_id = Column(Integer, ForeignKey("bots.id"))
    
    bot = relationship("Bot", back_populates="faqs")

# Create database
engine = create_engine("sqlite:///chatbot_builder.db", connect_args={"check_same_thread": False})
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Gemini setup (optional)
try:
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel('gemini-pro')
    GEMINI_AVAILABLE = True
    print("✅ Gemini API configured")
except:
    GEMINI_AVAILABLE = False
    print("⚠️ Gemini not available - using fallback")

# ============ Pydantic Models ============
class UserCreate(BaseModel):
    email: str
    name: str

class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    api_key: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class BotCreate(BaseModel):
    name: str
    description: str = ""
    welcome_message: str = "Hello! How can I help you today?"
    primary_color: str = "#007bff"
    position: str = "bottom-right"
    theme: str = "light"

class BotUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    welcome_message: Optional[str] = None
    primary_color: Optional[str] = None
    is_active: Optional[bool] = None

class BotResponse(BaseModel):
    id: int
    name: str
    description: str
    welcome_message: str
    primary_color: str
    position: str
    is_active: bool
    theme: str
    created_at: datetime
    total_conversations: int
    satisfaction_score: float
    faq_count: int = 0
    
    class Config:
        from_attributes = True

class FAQCreate(BaseModel):
    question: str
    answer: str
    category: str = "General"
    priority: int = 0

class FAQResponse(BaseModel):
    id: int
    question: str
    answer: str
    category: str
    priority: int
    times_asked: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# ============ User Endpoints ============
@app.post("/users", response_model=UserResponse)
def create_user(user: UserCreate, db=Depends(get_db)):
    """Create a new user"""
    existing = db.query(User).filter(User.email == user.email).first()
    if existing:
        return existing
    
    new_user = User(email=user.email, name=user.name)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    print(f"✅ Created user: {new_user.name} (ID: {new_user.id})")
    return new_user

@app.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db=Depends(get_db)):
    """Get user by ID"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    return user

# ============ Bot Endpoints ============
@app.post("/users/{user_id}/bots", response_model=BotResponse)
def create_bot(user_id: int, bot: BotCreate, db=Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    
    new_bot = Bot(**bot.dict(), user_id=user_id)
    db.add(new_bot)
    db.commit()
    db.refresh(new_bot)
    return new_bot

@app.get("/users/{user_id}/bots", response_model=List[BotResponse])
def get_user_bots(user_id: int, db=Depends(get_db)):
    bots = db.query(Bot).filter(Bot.user_id == user_id).all()
    for bot in bots:
        bot.faq_count = db.query(FAQ).filter(FAQ.bot_id == bot.id).count()
    return bots

@app.get("/bots/{bot_id}", response_model=BotResponse)
def get_bot(bot_id: int, db=Depends(get_db)):
    bot = db.query(Bot).filter(Bot.id == bot_id).first()
    if not bot:
        raise HTTPException(404, "Bot not found")
    bot.faq_count = db.query(FAQ).filter(FAQ.bot_id == bot.id).count()
    return bot

@app.put("/bots/{bot_id}", response_model=BotResponse)
def update_bot(bot_id: int, bot_update: BotUpdate, db=Depends(get_db)):
    bot = db.query(Bot).filter(Bot.id == bot_id).first()
    if not bot:
        raise HTTPException(404, "Bot not found")
    
    for key, value in bot_update.dict(exclude_unset=True).items():
        setattr(bot, key, value)
    
    db.commit()
    db.refresh(bot)
    return bot

@app.delete("/bots/{bot_id}")
def delete_bot(bot_id: int, db=Depends(get_db)):
    bot = db.query(Bot).filter(Bot.id == bot_id).first()
    if not bot:
        raise HTTPException(404, "Bot not found")
    
    db.delete(bot)
    db.commit()
    return {"message": "Bot deleted"}

# ============ FAQ Endpoints ============
@app.post("/bots/{bot_id}/faqs", response_model=FAQResponse)
def create_faq(bot_id: int, faq: FAQCreate, db=Depends(get_db)):
    bot = db.query(Bot).filter(Bot.id == bot_id).first()
    if not bot:
        raise HTTPException(404, "Bot not found")
    
    new_faq = FAQ(**faq.dict(), bot_id=bot_id)
    db.add(new_faq)
    db.commit()
    db.refresh(new_faq)
    return new_faq

@app.get("/bots/{bot_id}/faqs", response_model=List[FAQResponse])
def get_faqs(bot_id: int, db=Depends(get_db)):
    return db.query(FAQ).filter(FAQ.bot_id == bot_id).order_by(FAQ.priority.desc()).all()

@app.delete("/faqs/{faq_id}")
def delete_faq(faq_id: int, db=Depends(get_db)):
    faq = db.query(FAQ).filter(FAQ.id == faq_id).first()
    if not faq:
        raise HTTPException(404, "FAQ not found")
    
    db.delete(faq)
    db.commit()
    return {"message": "FAQ deleted"}

# ============ Categories Endpoint ============
@app.get("/bots/{bot_id}/categories")
def get_categories(bot_id: int, db=Depends(get_db)):
    """Get all unique categories for a bot"""
    categories = db.query(FAQ.category).filter(FAQ.bot_id == bot_id).distinct().all()
    return {"categories": [c[0] for c in categories if c[0] and c[0] != "General"]}

# ============ Analytics Endpoint ============
@app.get("/bots/{bot_id}/analytics")
def get_analytics(bot_id: int, days: int = 30, db=Depends(get_db)):
    """Get analytics for a bot"""
    
    bot = db.query(Bot).filter(Bot.id == bot_id).first()
    if not bot:
        raise HTTPException(404, "Bot not found")
    
    faqs = db.query(FAQ).filter(FAQ.bot_id == bot_id).all()
    
    # Get top questions
    top_questions = [
        {
            "question": faq.question,
            "times_asked": faq.times_asked or 0
        }
        for faq in sorted(faqs, key=lambda x: x.times_asked or 0, reverse=True)[:5]
        if faq.times_asked and faq.times_asked > 0
    ]
    
    # Generate daily activity (placeholder)
    daily_activity = []
    for i in range(min(days, 30)):
        date = (datetime.utcnow() - timedelta(days=i)).strftime("%Y-%m-%d")
        daily_activity.append({"date": date, "count": 0})
    
    categories = list(set([faq.category for faq in faqs if faq.category]))
    
    return {
        "total_conversations": bot.total_conversations or 0,
        "satisfaction_rate": bot.satisfaction_score or 0.0,
        "avg_response_time": 2000,
        "top_questions": top_questions,
        "daily_activity": daily_activity[::-1],
        "categories": len(categories)
    }

# ============ Chat Endpoint ============
@app.post("/chat")
async def chat(request: dict, db=Depends(get_db)):
    bot_id = request.get("bot_id")
    message = request.get("message", "")
    
    bot = db.query(Bot).filter(Bot.id == bot_id).first()
    if not bot:
        return {"answer": "Bot not found"}
    
    faqs = db.query(FAQ).filter(FAQ.bot_id == bot_id).all()
    
    if not faqs:
        return {"answer": "No FAQs configured yet. Add some questions and answers in the admin dashboard."}
    
    message_lower = message.lower()
    best_match = None
    best_score = 0
    
    for faq in faqs:
        score = sum(1 for word in faq.question.lower().split() if word in message_lower)
        if score > best_score:
            best_score = score
            best_match = faq
    
    if best_match and best_score > 0:
        best_match.times_asked += 1
        bot.total_conversations += 1
        db.commit()
        return {"answer": best_match.answer}
    
    bot.total_conversations += 1
    db.commit()
    return {"answer": "I don't have an answer for that yet. Please check back later or contact support."}

# ============ Embed Code Endpoint ============
@app.get("/bots/{bot_id}/embed-code")
def get_embed_code(bot_id: int, db=Depends(get_db)):
    bot = db.query(Bot).filter(Bot.id == bot_id).first()
    if not bot:
        raise HTTPException(404, "Bot not found")
    
    embed_code = f"""<!-- AI Chatbot Widget -->
<script>
  window.chatbotConfig = {{
    botId: {bot_id},
    apiUrl: "http://localhost:8000",
    primaryColor: "{bot.primary_color}",
    welcomeMessage: "{bot.welcome_message}"
  }};
  (function() {{
    var script = document.createElement('script');
    script.src = "http://localhost:8000/embed.js";
    document.body.appendChild(script);
  }})();
</script>
<!-- End Chatbot Widget -->"""
    
    return {"embed_code": embed_code}

# ============ Root ============
@app.get("/")
def root():
    return {"message": "AI Chatbot Builder API", "status": "running"}

if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*50)
    print("🚀 AI Chatbot Builder API")
    print("="*50)
    print("📡 Server: http://localhost:8000")
    print("📖 API Docs: http://localhost:8000/docs")
    print("="*50 + "\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)