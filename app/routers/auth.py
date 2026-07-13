from fastapi import APIRouter, Depends, HTTPException
from app.database import create_user, get_user_by_email
from app.models import UserCreate, UserLogin, TokenResponse
from app.auth import get_current_user, hash_password, verify_password, create_access_token

router = APIRouter()

@router.post("/auth/register")
def user_register(register_info: UserCreate):
    hashed_password = hash_password(register_info.password)
    create_user(email=register_info.email, hashed_password=hashed_password)
    return {"message": "User registration endpoint"}


@router.post("/auth/login", response_model=TokenResponse)
def user_login(login_info: UserLogin):
    user = get_user_by_email(login_info.email)

    if user is None or not verify_password(login_info.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token({"sub": user["email"]})
    return TokenResponse(access_token=access_token)

@router.get("/auth/me")
def read_current_user(current_user: dict = Depends(get_current_user)):
    return current_user