from typing import Optional, List
import strawberry
from strawberry.fastapi import GraphQLRouter
from strawberry.types import Info
from sqlalchemy.orm import Session
from jose import JWTError, jwt

from app.database import get_db
from app.models import User as UserModel, Post as PostModel, Comment as CommentModel
from app.auth import hash_password, verify_password, create_token
from app.config import settings

# ─── Types ───────────────────────────────────────────────────────────────────

@strawberry.type
class User:
    id: str
    email: str
    username: str
    created_at: str

@strawberry.type
class Comment:
    id: str
    content: str
    created_at: str
    author: User

@strawberry.type
class Post:
    id: str
    title: str
    content: str
    published: bool
    created_at: str
    updated_at: str
    author: User
    comments: List[Comment]

@strawberry.type
class AuthPayload:
    accessToken: str
    user: User

# ─── Helpers ─────────────────────────────────────────────────────────────────

def get_db_from_info(info: Info) -> Session:
    return info.context["db"]

def get_user_from_info(info: Info) -> UserModel | None:
    request = info.context.get("request")
    if not request:
        return None
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        return None
    token = auth.split(" ")[1]
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        user_id = payload.get("sub")
        if not user_id:
            return None
        return get_db_from_info(info).query(UserModel).filter(UserModel.id == user_id).first()
    except JWTError:
        return None

def require_user(info: Info) -> UserModel:
    user = get_user_from_info(info)
    if not user:
        raise Exception("Authentication required")
    return user

def user_to_type(u: UserModel) -> User:
    return User(id=u.id, email=u.email, username=u.username or "", created_at=u.created_at.isoformat())

def post_to_type(p: PostModel, db: Session) -> Post:
    return Post(
        id=p.id, title=p.title, content=p.content, published=p.published,
        created_at=p.created_at.isoformat(), updated_at=p.updated_at.isoformat(),
        author=user_to_type(p.author),
        comments=[comment_to_type(c) for c in p.comments],
    )

def comment_to_type(c: CommentModel) -> Comment:
    return Comment(id=c.id, content=c.content, created_at=c.created_at.isoformat(), author=user_to_type(c.author))

# ─── Queries ─────────────────────────────────────────────────────────────────

@strawberry.type
class BlogQuery:
    @strawberry.field
    def posts(self, info: Info) -> List[Post]:
        db = get_db_from_info(info)
        return [post_to_type(p, db) for p in db.query(PostModel).order_by(PostModel.created_at.desc()).all()]

    @strawberry.field
    def post(self, id: str, info: Info) -> Optional[Post]:
        db = get_db_from_info(info)
        p = db.query(PostModel).filter(PostModel.id == id).first()
        return post_to_type(p, db) if p else None

    @strawberry.field
    def me(self, info: Info) -> Optional[User]:
        u = get_user_from_info(info)
        return user_to_type(u) if u else None

# ─── Mutations ───────────────────────────────────────────────────────────────

@strawberry.input
class RegisterInput:
    email: str
    username: str
    password: str

@strawberry.input
class LoginInput:
    email: str
    password: str

@strawberry.input
class CreatePostInput:
    title: str
    content: str
    published: bool = True

@strawberry.input
class UpdatePostInput:
    id: str
    title: Optional[str] = None
    content: Optional[str] = None
    published: Optional[bool] = None

@strawberry.input
class CreateCommentInput:
    postId: str
    content: str

@strawberry.type
class BlogMutation:
    @strawberry.mutation
    def register(self, input: RegisterInput, info: Info) -> AuthPayload:
        db = get_db_from_info(info)
        existing = db.query(UserModel).filter(
            (UserModel.email == input.email) | (UserModel.username == input.username)
        ).first()
        if existing:
            raise Exception("Email or username already taken")
        user = UserModel(email=input.email, username=input.username, hashed_password=hash_password(input.password))
        db.add(user)
        db.commit()
        db.refresh(user)
        token = create_token({"sub": user.id})
        return AuthPayload(accessToken=token, user=user_to_type(user))

    @strawberry.mutation
    def login(self, input: LoginInput, info: Info) -> AuthPayload:
        db = get_db_from_info(info)
        user = db.query(UserModel).filter(UserModel.email == input.email).first()
        if not user or not verify_password(input.password, user.hashed_password):
            raise Exception("Invalid credentials")
        token = create_token({"sub": user.id})
        return AuthPayload(accessToken=token, user=user_to_type(user))

    @strawberry.mutation
    def create_post(self, input: CreatePostInput, info: Info) -> Post:
        db = get_db_from_info(info)
        user = require_user(info)
        post = PostModel(title=input.title, content=input.content, published=input.published, author_id=user.id)
        db.add(post)
        db.commit()
        db.refresh(post)
        return post_to_type(post, db)

    @strawberry.mutation
    def update_post(self, input: UpdatePostInput, info: Info) -> Post:
        db = get_db_from_info(info)
        user = require_user(info)
        post = db.query(PostModel).filter(PostModel.id == input.id, PostModel.author_id == user.id).first()
        if not post:
            raise Exception("Post not found or not yours")
        if input.title is not None: post.title = input.title
        if input.content is not None: post.content = input.content
        if input.published is not None: post.published = input.published
        db.commit()
        db.refresh(post)
        return post_to_type(post, db)

    @strawberry.mutation
    def delete_post(self, id: str, info: Info) -> bool:
        db = get_db_from_info(info)
        user = require_user(info)
        post = db.query(PostModel).filter(PostModel.id == id, PostModel.author_id == user.id).first()
        if not post:
            raise Exception("Post not found or not yours")
        db.delete(post)
        db.commit()
        return True

    @strawberry.mutation
    def add_comment(self, input: CreateCommentInput, info: Info) -> Comment:
        db = get_db_from_info(info)
        user = require_user(info)
        post = db.query(PostModel).filter(PostModel.id == input.postId).first()
        if not post:
            raise Exception("Post not found")
        comment = CommentModel(content=input.content, author_id=user.id, post_id=input.postId)
        db.add(comment)
        db.commit()
        db.refresh(comment)
        return comment_to_type(comment)

# ─── Schema ──────────────────────────────────────────────────────────────────

from fastapi import Depends
from sqlalchemy.orm import Session
from app.database import get_db

async def get_blog_context(db: Session = Depends(get_db)):
    return {"db": db}

blog_schema = strawberry.Schema(query=BlogQuery, mutation=BlogMutation)
blog_router = GraphQLRouter(blog_schema, prefix="/api/blog", context_getter=get_blog_context)
