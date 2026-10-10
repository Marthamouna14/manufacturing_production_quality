from datetime import datetime,timedelta,timezone
from jose import jwt,JWTError
from passlib.context import CryptContext
from fastapi import Depends,HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.config import settings
from app.db.session import get_db
from app.models import User
pwd=CryptContext(schemes=["bcrypt"],deprecated="auto")
oauth2=OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
def hash_password(v): return pwd.hash(v)
def verify_password(v,h): return pwd.verify(v,h)
def token(sub,typ,minutes):
    now=datetime.now(timezone.utc)
    return jwt.encode({"sub":str(sub),"type":typ,"iat":now,"exp":now+timedelta(minutes=minutes)},settings.secret_key,algorithm="HS256")
def current_user(t:str=Depends(oauth2),db:Session=Depends(get_db)):
    try:
        p=jwt.decode(t,settings.secret_key,algorithms=["HS256"])
        if p.get("type")!="access": raise HTTPException(401,"Invalid access token")
        u=db.get(User,int(p["sub"]))
    except (JWTError,ValueError): raise HTTPException(401,"Invalid or expired token")
    if not u or not u.is_active: raise HTTPException(401,"Inactive or missing user")
    return u
def roles(*allowed):
    def check(u=Depends(current_user)):
        if u.role not in allowed: raise HTTPException(403,"Insufficient role permissions")
        return u
    return check
