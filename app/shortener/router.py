import secrets
import string
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import ShortURL, User
from app.auth import get_current_user
from pydantic import BaseModel

router = APIRouter(prefix="/api/shortener", tags=["URL Shortener"])

class URLOut(BaseModel):
    id: str
    short_code: str
    target_url: str
    clicks: int
    is_active: bool

class URLStats(BaseModel):
    short_code: str
    target_url: str
    clicks: int
    total: int

def gen_short() -> str:
    chars = string.ascii_letters + string.digits
    return ''.join(secrets.choice(chars) for _ in range(6))

@router.post("/shorten", response_model=URLOut)
def shorten(target_url: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    short = gen_short()
    while db.query(ShortURL).filter(ShortURL.short_code == short).first():
        short = gen_short()
    url = ShortURL(short_code=short, target_url=target_url, owner_id=user.id)
    db.add(url)
    db.commit()
    db.refresh(url)
    return URLOut(id=url.id, short_code=url.short_code, target_url=url.target_url, clicks=url.clicks, is_active=url.is_active)

@router.get("/my", response_model=list[URLOut])
def my_urls(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    urls = db.query(ShortURL).filter(ShortURL.owner_id == user.id).order_by(ShortURL.created_at.desc()).all()
    return [URLOut(id=u.id, short_code=u.short_code, target_url=u.target_url, clicks=u.clicks, is_active=u.is_active) for u in urls]

@router.get("/{short_code}/stats", response_model=URLStats)
def stats(short_code: str, db: Session = Depends(get_db)):
    url = db.query(ShortURL).filter(ShortURL.short_code == short_code).first()
    if not url:
        raise HTTPException(status_code=404)
    return URLStats(short_code=url.short_code, target_url=url.target_url, clicks=url.clicks, total=url.clicks)

@router.delete("/{short_code}", status_code=204)
def delete(short_code: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    url = db.query(ShortURL).filter(ShortURL.short_code == short_code, ShortURL.owner_id == user.id).first()
    if not url:
        raise HTTPException(status_code=404)
    db.delete(url)
    db.commit()

@router.get("/r/{short_code}")
def redirect(short_code: str, db: Session = Depends(get_db)):
    url = db.query(ShortURL).filter(ShortURL.short_code == short_code, ShortURL.is_active == True).first()
    if not url:
        raise HTTPException(status_code=404)
    url.clicks += 1
    db.commit()
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=url.target_url, status_code=302)
