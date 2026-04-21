from datetime import datetime
from enum import Enum
from typing import Any, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class ReportStatus(str, Enum):
    PROCESSING = "processing"  # file uploaded, extraction in progress
    PENDING = "pending"  # extraction done, awaiting doctor review
    REVIEWED = "reviewed"
    ARCHIVED = "archived"


class TestSchema(BaseModel):
    name: str = Field(..., example="Haemoglobin")
    result: Optional[str] = Field(None, example="13.5")
    unit: Optional[str] = Field(None, example="g/dL")
    reference_range: Optional[str] = Field(None, example="12.0 - 17.0")

    @field_validator("reference_range", mode="before")
    @classmethod
    def coerce_to_string(cls, v: Any) -> Optional[str]:
        if v is None:
            return None
        if isinstance(v, dict):
            return ", ".join(f"{k}: {val}" for k, val in v.items())
        return str(v)


# ---- inbound ----------------------------------------------------------------


class ReportCreateSchema(BaseModel):
    """Only what the caller supplies — medical data is extracted later."""

    patient_id: UUID
    patient_name: str = Field(..., min_length=2, max_length=100)


class ReportUpdateSchema(BaseModel):
    patient_name: Optional[str] = None
    tests: Optional[List[TestSchema]] = None
    doctor: Optional[str] = None
    lab_no: Optional[str] = None
    status: Optional[ReportStatus] = None


# ---- DB / response ----------------------------------------------------------


class ReportInDBSchema(ReportCreateSchema):
    id: UUID = Field(default_factory=uuid4)
    url: Optional[str] = None
    # medical fields — filled by background extraction
    tests: Optional[List[TestSchema]] = None
    doctor: Optional[str] = None
    lab_no: Optional[str] = None
    status: ReportStatus = Field(ReportStatus.PROCESSING)
    created_at: datetime = Field(default_factory=datetime.now)


class ReportResponseSchema(BaseModel):
    id: UUID
    patient_id: UUID
    patient_name: str
    url: Optional[str] = None
    file_data: Optional[str] = None
    tests: Optional[List[TestSchema]] = None
    doctor: Optional[str] = None
    lab_no: Optional[str] = None
    status: ReportStatus
    created_at: datetime

    model_config = {"from_attributes": True}
