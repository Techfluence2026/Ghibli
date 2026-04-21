from datetime import datetime

from pydantic import UUID4, BaseModel, EmailStr


class SigninRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    phone: str


class SigninResponse(BaseModel):
    id: UUID4
    username: str
    email: EmailStr
    phone: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserSchema(BaseModel):
    id: UUID4
    username: str
    email: EmailStr
    phone: str

    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    session_id: str
    access_token: str
    access_token_expires_at: datetime
    refresh_token: str
    refresh_token_expires_at: datetime
    user: UserSchema


class RenewAccessTokenRequest(BaseModel):
    refresh_token: str


class RenewAccessTokenResponse(BaseModel):
    access_token: str
    access_token_expires_at: datetime
