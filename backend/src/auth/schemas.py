from datetime import datetime
from enum import Enum
from typing import List, Optional

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


class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


class BloodGroup(str, Enum):
    AP = "A+"
    AN = "A-"
    BP = "b+"
    BN = "B-"
    ABP = "AB+"
    ABN = "AB-"
    OP = "O+"
    ON = "O-"


class UpdateUserDetailsSchemaRequest(BaseModel):
    id: UUID4
    age: int
    gender: Gender
    height: float
    weight: float
    blood_group: BloodGroup
    medical_history: Optional[str] = None
    allergies: Optional[List[str]] = None
    timezone: Optional[str] = None


class MeResponse(BaseModel):
    id: UUID4
    username: str
    email: EmailStr
    phone: str
    age: Optional[int] = None
    gender: Optional[str] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    blood_group: Optional[str] = None
    medical_history: Optional[str] = None
    allergies: Optional[List[str]] = None
    diseases: Optional[List[str]] = None
    timezone: Optional[str] = None

    class Config:
        from_attributes = True
