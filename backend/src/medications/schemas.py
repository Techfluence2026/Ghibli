from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class MedicationCreateSchema(BaseModel):
    name: str = Field(..., example="Amoxicillin")
    dose: str = Field(..., example="500mg")
    times: List[str] = Field(..., example=["08:00", "20:00"])


class MedicationUpdateSchema(BaseModel):
    name: Optional[str] = None
    dose: Optional[str] = None
    times: Optional[List[str]] = None


class MedicationResponseSchema(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    dose: str
    times: List[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class MedicationInDBSchema(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    name: str
    dose: str
    times: List[str]
    # FIX: use timezone-aware UTC datetime instead of naive datetime.now()
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))