from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ReportStatus(str, Enum):
    PENDING  = "pending"
    REVIEWED = "reviewed"
    ARCHIVED = "archived"


class TestSchema(BaseModel):
    name:            str = Field(..., example="Haemoglobin")
    result:          str = Field(..., example="13.5")
    unit:            str = Field(..., example="g/dL")
    reference_range: str = Field(..., example="12.0 - 17.0")


class ReportCreateSchema(BaseModel):
    patient_id:   UUID
    patient_name: str              = Field(..., min_length=2, max_length=100)
    tests:        List[TestSchema]
    doctor:       str              = Field(..., max_length=100)
    lab_no:       str              = Field(..., max_length=100)
    status:       ReportStatus     = Field(ReportStatus.PENDING)


class ReportUpdateSchema(BaseModel):
    patient_name: Optional[str]            = None
    tests:        Optional[List[TestSchema]] = None
    doctor:       Optional[str]            = None
    lab_no:       Optional[str]            = None
    status:       Optional[ReportStatus]   = None


class ReportResponseSchema(BaseModel):
    id:           UUID
    patient_id:   UUID
    patient_name: str
    url:          Optional[str]       = None
    tests:        List[TestSchema]
    doctor:       str
    lab_no:       str
    status:       ReportStatus
    created_at:   datetime

    model_config = {"from_attributes": True}


class ReportInDBSchema(ReportCreateSchema):
    id:         UUID     = Field(default_factory=uuid4)
    url:        Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)