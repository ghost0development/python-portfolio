from pathlib import Path

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import engine, Base, get_db
from app.auth import get_current_user
from app.models import User
from app.shortener.router import router as shortener_router
from app.blog.schema import blog_router as blog_graphql_router
from app.chat.router import router as chat_router
from app.queue.router import router as queue_router
from app.rag.router import router as rag_router


# ─── Auth models ───────────────────────────────────────────────────────────

class AuthBody(BaseModel):
    email: str
    password: str

class RegisterBody(BaseModel):
    email: str
    username: str
    password: str

# ─── Auth endpoint (shared) ────────────────────────────────────────────────
from fastapi import APIRouter
auth_router = APIRouter(prefix="/auth", tags=["auth"])

@auth_router.post("/register")
def register(body: RegisterBody, db: Session = Depends(get_db)):
    from app.auth import hash_password, create_token
    existing = db.query(User).filter((User.email == body.email) | (User.username == body.username)).first()
    if existing:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Email or username already taken")
    user = User(email=body.email, username=body.username, hashed_password=hash_password(body.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_token({"sub": user.id})
    return {"access_token": token, "token_type": "bearer"}

@auth_router.post("/login")
def login(body: AuthBody, db: Session = Depends(get_db)):
    from app.auth import verify_password, create_token
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.hashed_password):
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token({"sub": user.id})
    return {"access_token": token, "token_type": "bearer"}

@auth_router.get("/me")
def me(user: User = Depends(get_current_user)):
    return {"id": user.id, "email": user.email, "username": user.username}

# ─── App ────────────────────────────────────────────────────────────────────

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Portfolio API", version="1.0.0",
              description="Unified API: All 5 portfolio projects",
              docs_url="/docs")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# Mount all modules
app.include_router(auth_router)
app.include_router(shortener_router)
app.include_router(blog_graphql_router)
app.include_router(chat_router, prefix="/api/chat")
app.include_router(queue_router, prefix="/api/queue")
app.include_router(rag_router, prefix="/api/rag")
# Health
@app.get("/health")
def health():
    return {"status": "ok", "modules": ["shortener", "blog", "chat", "queue", "rag"]}

# Frontend (static files) – optional
static_dir = Path(__file__).parent.parent / "frontend" / "dist"
if static_dir.exists():
    app.mount("/assets", StaticFiles(directory=str(static_dir / "assets")), name="assets")
    @app.api_route("/{full_path:path}", methods=["GET"])
    def serve_frontend(full_path: str):
        file = static_dir / full_path
        if file.exists() and file.is_file():
            return FileResponse(str(file))
        return FileResponse(str(static_dir / "index.html"))
