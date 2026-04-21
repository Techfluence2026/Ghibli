from pydantic import EmailStr
from datetime import datetime
from typing import List
from uuid import UUID, uuid4


class User:
    id: UUID
    email: str
    username: str
    phone: str
    age: int
    blood_group: str
    diseases: List[str]
    allergies: List[str]
    height: float
    weight: float
    gender: str
    created_at: datetime

    def __init__(self):
        self.id = uuid4()
        self.created_at = datetime.now()

class Session:
    id:UUID
    user_email: EmailStr
    refresh_token:str
    is_revoked: bool
    expires_at: datetime

    def __init__(self):
        self.id=uuid4() 