from fastapi import FastAPI, APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timedelta
import jwt
from passlib.context import CryptContext
from emergentintegrations.llm.chat import LlmChat, UserMessage

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Security setup
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# Create the main app without a prefix
app = FastAPI(title="Code Learning Platform API", version="1.0.0")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# LLM Chat setup
EMERGENT_LLM_KEY = os.getenv("EMERGENT_LLM_KEY")

# Models
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    username: str
    hashed_password: str
    preferred_languages: List[str] = Field(default_factory=lambda: ["python"])
    skill_level: str = "beginner"  # beginner, intermediate, advanced
    explanation_language: str = "english"  # english, hindi, hinglish
    created_at: datetime = Field(default_factory=datetime.utcnow)
    total_xp: int = 0
    streak_days: int = 0
    last_activity: datetime = Field(default_factory=datetime.utcnow)

class UserCreate(BaseModel):
    email: str
    username: str
    password: str
    preferred_languages: Optional[List[str]] = ["python"]
    skill_level: Optional[str] = "beginner"
    explanation_language: Optional[str] = "english"

class UserLogin(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class CodeExplanationRequest(BaseModel):
    code: str
    language: str
    line_number: Optional[int] = None
    explanation_level: str = "beginner"  # beginner, intermediate, advanced

class CodeExplanationResponse(BaseModel):
    explanation: str
    short_explanation: str
    confidence_score: float
    suggestions: List[str] = []

class CodeSnippet(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    title: str
    code: str
    language: str
    explanations: Dict[int, Dict] = Field(default_factory=dict)  # line_number -> explanation
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class PracticeQuestion(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    question_type: str  # mcq, fill_blank, debug, complexity
    question_text: str
    code_snippet: Optional[str] = None
    options: Optional[List[str]] = None  # for MCQ
    correct_answer: str
    explanation: str
    difficulty: str = "beginner"
    language: str = "python"
    created_at: datetime = Field(default_factory=datetime.utcnow)

# Utility functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    # Truncate password to 72 bytes for bcrypt compatibility
    password_bytes = password.encode('utf-8')[:72]
    return pwd_context.hash(password_bytes.decode('utf-8'))

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    
    user = await db.users.find_one({"id": user_id})
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return User(**user)

# Authentication Routes
@api_router.post("/auth/register", response_model=Token)
async def register(user_data: UserCreate):
    # Check if user already exists
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Check username
    existing_username = await db.users.find_one({"username": user_data.username})
    if existing_username:
        raise HTTPException(status_code=400, detail="Username already taken")
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    user_dict = user_data.dict()
    user_dict.pop("password")
    user_dict["hashed_password"] = hashed_password
    
    new_user = User(**user_dict)
    await db.users.insert_one(new_user.dict())
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": new_user.id}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@api_router.post("/auth/login", response_model=Token)
async def login(user_credentials: UserLogin):
    user = await db.users.find_one({"email": user_credentials.email})
    if not user or not verify_password(user_credentials.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["id"]}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@api_router.get("/auth/me", response_model=User)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    return current_user

# Code Explanation Routes
@api_router.post("/code/explain", response_model=CodeExplanationResponse)
async def explain_code(
    request: CodeExplanationRequest,
    current_user: User = Depends(get_current_user)
):
    try:
        # Create system message based on user preferences
        system_message = f"""You are an expert code tutor specializing in {request.language} programming.
        Explanation level: {request.explanation_level}
        Explanation language: {current_user.explanation_language}
        
        Provide code explanations that are:
        - Clear and appropriate for {request.explanation_level} level
        - In {current_user.explanation_language} language
        - Include both short (1-2 sentences) and detailed explanations
        - Offer practical suggestions for improvement
        - Rate your confidence (0.0 to 1.0) in the explanation
        """
        
        # Initialize LLM Chat
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"code_explanation_{current_user.id}_{uuid.uuid4()}",
            system_message=system_message
        ).with_model("gemini", "gemini-2.0-flash")
        
        # Create user message
        if request.line_number:
            user_text = f"""Explain line {request.line_number} of this {request.language} code:

```{request.language}
{request.code}
```

Please provide:
1. A short explanation (1-2 sentences)
2. A detailed explanation
3. Your confidence score (0.0 to 1.0)
4. 2-3 practical suggestions

Format your response as JSON with keys: short_explanation, detailed_explanation, confidence_score, suggestions"""
        else:
            user_text = f"""Explain this {request.language} code:

```{request.language}
{request.code}
```

Please provide:
1. A short explanation (1-2 sentences) 
2. A detailed explanation
3. Your confidence score (0.0 to 1.0)
4. 2-3 practical suggestions

Format your response as JSON with keys: short_explanation, detailed_explanation, confidence_score, suggestions"""
        
        user_message = UserMessage(text=user_text)
        
        # Get response from LLM
        response = await chat.send_message(user_message)
        
        # Parse the response (try to extract JSON or use fallback)
        try:
            import json
            parsed_response = json.loads(response)
            return CodeExplanationResponse(
                explanation=parsed_response.get("detailed_explanation", response),
                short_explanation=parsed_response.get("short_explanation", response[:100]),
                confidence_score=parsed_response.get("confidence_score", 0.8),
                suggestions=parsed_response.get("suggestions", [])
            )
        except:
            # Fallback if JSON parsing fails
            return CodeExplanationResponse(
                explanation=response,
                short_explanation=response[:100] + "..." if len(response) > 100 else response,
                confidence_score=0.8,
                suggestions=["Consider adding comments", "Review variable naming"]
            )
            
    except Exception as e:
        logging.error(f"Error explaining code: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to explain code")

# Code Snippet Management
@api_router.post("/code/snippets", response_model=CodeSnippet)
async def save_code_snippet(
    title: str,
    code: str,
    language: str,
    current_user: User = Depends(get_current_user)
):
    snippet = CodeSnippet(
        user_id=current_user.id,
        title=title,
        code=code,
        language=language
    )
    await db.code_snippets.insert_one(snippet.dict())
    return snippet

@api_router.get("/code/snippets", response_model=List[CodeSnippet])
async def get_user_snippets(current_user: User = Depends(get_current_user)):
    snippets = await db.code_snippets.find({"user_id": current_user.id}).to_list(100)
    return [CodeSnippet(**snippet) for snippet in snippets]

# Practice Questions (Mock for now)
@api_router.get("/practice/questions", response_model=List[PracticeQuestion])
async def get_practice_questions(
    language: str = "python",
    difficulty: str = "beginner",
    current_user: User = Depends(get_current_user)
):
    # Mock practice questions for now
    mock_questions = [
        PracticeQuestion(
            question_type="mcq",
            question_text="What does this Python code do?\n\n```python\nprint('Hello, World!')\n```",
            options=["Prints text to console", "Creates a variable", "Imports a module", "Defines a function"],
            correct_answer="Prints text to console",
            explanation="The print() function displays the given text on the console.",
            difficulty=difficulty,
            language=language
        ),
        PracticeQuestion(
            question_type="fill_blank",
            question_text="Complete the code to create a variable:\n\n```python\n___ = 'Hello'\n```",
            correct_answer="name",
            explanation="Variables in Python are created by assigning a value to a name.",
            difficulty=difficulty,
            language=language
        )
    ]
    return mock_questions

# Dashboard/Stats Routes
@api_router.get("/dashboard/stats")
async def get_dashboard_stats(current_user: User = Depends(get_current_user)):
    # Get user's code snippets count
    snippets_count = await db.code_snippets.count_documents({"user_id": current_user.id})
    
    # Mock stats for now
    return {
        "user": {
            "username": current_user.username,
            "total_xp": current_user.total_xp,
            "streak_days": current_user.streak_days,
            "skill_level": current_user.skill_level
        },
        "activity": {
            "snippets_created": snippets_count,
            "questions_solved": 0,  # Will implement later
            "explanations_viewed": 0  # Will implement later
        },
        "progress": {
            "concepts_mastered": 0,
            "current_level": 1,
            "next_level_xp": 100
        }
    }

# Health check routes
@api_router.get("/")
async def root():
    return {"message": "Code Learning Platform API", "status": "running"}

@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow()}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()