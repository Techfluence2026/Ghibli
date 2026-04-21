from pydantic import UUID, BaseModel, EmailStr, datetime


class User(BaseModel):
    username: str
    email: EmailStr
    password: str
    age: int
    phone: str


class Session(BaseModel):
    pass


class SigninRequest(User):
    pass


class SigninResponse(User):
    id: UUID


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    session_id: str
    access_token: str
    access_token_expires_at: datetime
    refresh_token: str
    refresh_token_expires_at: datetime
    user: User


class RenewAccessTokenRequest(BaseModel):
    refresh_token: str


class RenewAccessTokenResponse(BaseModel):
    access_token: str
    access_token_expires_at: datetime
