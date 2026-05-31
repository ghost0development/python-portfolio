import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship
from app.database import Base

def gen_id():
    return str(uuid.uuid4())[:8]

# ─── Shared: User ────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=gen_id)
    email = Column(String, unique=True, index=True)
    username = Column(String, unique=True, index=True, nullable=True)
    hashed_password = Column(String)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

# ─── Module: URL Shortener ──────────────────────────────────────────────────

class ShortURL(Base):
    __tablename__ = "short_urls"
    id = Column(String, primary_key=True, default=gen_id)
    short_code = Column(String, unique=True, index=True)
    target_url = Column(String)
    clicks = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    owner_id = Column(String, ForeignKey("users.id"), nullable=True)
    owner = relationship("User")

# ─── Module: GraphQL Blog ───────────────────────────────────────────────────

class Post(Base):
    __tablename__ = "posts"
    id = Column(String, primary_key=True, default=gen_id)
    title = Column(String)
    content = Column(Text)
    published = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    author_id = Column(String, ForeignKey("users.id"), nullable=False)
    author = relationship("User")
    comments = relationship("Comment", back_populates="post", cascade="all, delete-orphan")

class Comment(Base):
    __tablename__ = "comments"
    id = Column(String, primary_key=True, default=gen_id)
    content = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    author_id = Column(String, ForeignKey("users.id"), nullable=False)
    post_id = Column(String, ForeignKey("posts.id"), nullable=False)
    author = relationship("User")
    post = relationship("Post", back_populates="comments")
