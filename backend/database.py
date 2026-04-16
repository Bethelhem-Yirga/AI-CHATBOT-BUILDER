from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
from models import SessionLocal, User, Bot, FAQ, Conversation
import google.generativeai as genai
import os
import secrets

app = FastAPI(title="AI Chatbot Builder API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Gemini setup (optional)
try:
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel('gemini-pro')
    GEMINI_AVAILABLE = True
except:
    GEMINI_AVAILABLE = False
    print("⚠️ Gemini not available - using fallback mode")

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

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
    theme: Optional[str] = None

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
    faq_count: int
    
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
    helpful_count: int
    not_helpful_count: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class ChatRequest(BaseModel):
    bot_id: int
    message: str
    session_id: str

class ChatResponse(BaseModel):
    answer: str
    suggested_questions: List[str] = []

# ============ User Endpoints ============
@app.post("/users", response_model=UserResponse)
def create_user(user: UserCreate, db=Depends(get_db)):
    existing = db.query(User).filter(User.email == user.email).first()
    if existing:
        raise HTTPException(400, "User already exists")
    
    new_user = User(email=user.email, name=user.name)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db=Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    return user

# ============ Bot Management Endpoints ============
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
    
    # Add computed fields
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
    return {"message": "Bot deleted successfully"}

# ============ FAQ Management Endpoints ============
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
def get_faqs(bot_id: int, category: Optional[str] = None, db=Depends(get_db)):
    query = db.query(FAQ).filter(FAQ.bot_id == bot_id)
    if category:
        query = query.filter(FAQ.category == category)
    return query.order_by(FAQ.priority.desc()).all()

@app.put("/faqs/{faq_id}", response_model=FAQResponse)
def update_faq(faq_id: int, faq: FAQCreate, db=Depends(get_db)):
    existing = db.query(FAQ).filter(FAQ.id == faq_id).first()
    if not existing:
        raise HTTPException(404, "FAQ not found")
    
    for key, value in faq.dict().items():
        setattr(existing, key, value)
    
    db.commit()
    db.refresh(existing)
    return existing

@app.delete("/faqs/{faq_id}")
def delete_faq(faq_id: int, db=Depends(get_db)):
    faq = db.query(FAQ).filter(FAQ.id == faq_id).first()
    if not faq:
        raise HTTPException(404, "FAQ not found")
    
    db.delete(faq)
    db.commit()
    return {"message": "FAQ deleted"}

@app.get("/bots/{bot_id}/categories")
def get_categories(bot_id: int, db=Depends(get_db)):
    categories = db.query(FAQ.category).filter(FAQ.bot_id == bot_id).distinct().all()
    return {"categories": [c[0] for c in categories]}

# ============ Chat Endpoint ============
@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, db=Depends(get_db)):
    # Get bot
    bot = db.query(Bot).filter(Bot.id == request.bot_id).first()
    if not bot:
        raise HTTPException(404, "Bot not found")
    
    # Update bot stats
    bot.total_queries += 1
    
    # Get FAQs
    faqs = db.query(FAQ).filter(FAQ.bot_id == request.bot_id).order_by(FAQ.priority.desc()).all()
    
    if not faqs:
        return ChatResponse(
            answer="Please add some FAQs to this bot first! Go to the Admin Dashboard to add questions and answers.",
            suggested_questions=[]
        )
    
    # Build FAQ context
    faq_context = "\n".join([f"Q: {faq.question}\nA: {faq.answer}" for faq in faqs])
    
    # Generate response
    if GEMINI_AVAILABLE:
        try:
            prompt = f"""You are a customer support bot named "{bot.name}".
Welcome message: {bot.welcome_message}

Answer using ONLY these FAQs. Be concise and helpful:

{faq_context}

User question: {request.message}
Answer:"""
            
            response = model.generate_content(prompt)
            answer = response.text
        except:
            answer = get_fallback_answer(request.message, faqs)
    else:
        answer = get_fallback_answer(request.message, faqs)
    
    # Track FAQ usage
    for faq in faqs:
        if any(word in request.message.lower() for word in faq.question.lower().split()[:3]):
            faq.times_asked += 1
            break
    
    # Save conversation
    conversation = Conversation(
        session_id=request.session_id,
        user_message=request.message,
        bot_response=answer,
        bot_id=request.bot_id
    )
    db.add(conversation)
    
    # Update bot conversation count
    bot.total_conversations = db.query(Conversation).filter(Conversation.bot_id == request.bot_id).count()
    
    db.commit()
    
    # Get suggested questions
    suggested = [faq.question for faq in faqs[:3]]
    
    return ChatResponse(answer=answer, suggested_questions=suggested)

def get_fallback_answer(question: str, faqs: List[FAQ]) -> str:
    """Keyword matching fallback"""
    question_lower = question.lower()
    best_match = None
    best_score = 0
    
    for faq in faqs:
        score = sum(1 for word in faq.question.lower().split() if word in question_lower)
        if score > best_score:
            best_score = score
            best_match = faq
    
    if best_match and best_score > 0:
        return best_match.answer
    
    return "I don't have an answer for that yet. Please email support@example.com for assistance."

# ============ Analytics Endpoints ============
@app.get("/bots/{bot_id}/analytics")
def get_analytics(bot_id: int, days: int = 30, db=Depends(get_db)):
    bot = db.query(Bot).filter(Bot.id == bot_id).first()
    if not bot:
        raise HTTPException(404, "Bot not found")
    
    # Date range
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Get conversations
    conversations = db.query(Conversation).filter(
        Conversation.bot_id == bot_id,
        Conversation.created_at >= cutoff_date
    ).all()
    
    # Calculate analytics
    total = len(conversations)
    helpful = sum(1 for c in conversations if c.was_helpful == True)
    
    # Get top FAQs
    top_faqs = db.query(FAQ).filter(FAQ.bot_id == bot_id).order_by(FAQ.times_asked.desc()).limit(5).all()
    
    # Daily conversation counts
    daily_counts = {}
    for conv in conversations:
        date_str = conv.created_at.strftime("%Y-%m-%d")
        daily_counts[date_str] = daily_counts.get(date_str, 0) + 1
    
    return {
        "total_conversations": total,
        "helpful_responses": helpful,
        "satisfaction_rate": helpful / total if total > 0 else 0,
        "avg_response_time": sum(c.response_time_ms or 2000 for c in conversations) / total if total > 0 else 0,
        "top_questions": [
            {"question": faq.question, "times_asked": faq.times_asked}
            for faq in top_faqs
        ],
        "daily_activity": [{"date": k, "count": v} for k, v in daily_counts.items()],
        "categories": db.query(FAQ.category).filter(FAQ.bot_id == bot_id).distinct().count()
    }

@app.post("/conversations/{conv_id}/feedback")
def submit_feedback(conv_id: int, helpful: bool, db=Depends(get_db)):
    conv = db.query(Conversation).filter(Conversation.id == conv_id).first()
    if not conv:
        raise HTTPException(404, "Conversation not found")
    
    conv.was_helpful = helpful
    db.commit()
    
    return {"message": "Feedback recorded"}

# ============ Embed Code ============
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

if __name__ == "__main__":
    import uvicorn
    print("🚀 Admin Dashboard API running on http://localhost:8000")
    print("📊 API Docs: http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000)