from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


# ── Enums ───────────────────────────────────────────────────────────────────────

class PrescriptionStatus(str, Enum):
    ACTIVE   = "active"
    EXPIRED  = "expired"
    NEW = "new"


# ── Sub-schemas ─────────────────────────────────────────────────────────────────

class MedicineSchema(BaseModel):
    """A single medication entry inside a prescription."""
    name:      str = Field(..., example="Amoxicillin")
    dose:      str = Field(..., example="500mg")
    frequency: str = Field(..., example="3 times a day")


# ── Request schemas (what the API receives) ─────────────────────────────────────

class PrescriptionCreateSchema(BaseModel):
    """
    Schema for creating a new prescription.
    The prescription file is handled separately as a multipart upload
    (FastAPI UploadFile); the resulting S3 URL is injected before saving.
    """
    patient_id:      UUID              = Field(...)
    patient_name:    str               = Field(..., min_length=2, max_length=100)
    disease_date:    str               = Field(...)
    medications:     List[MedicineSchema]
    doctors_remark:  Optional[str]     = Field(None, max_length=1000)
    status:          PrescriptionStatus = Field(PrescriptionStatus.NEW)


class PrescriptionUpdateSchema(BaseModel):
    """All fields are optional — send only what changed."""
    patient_name:   Optional[str]               = None
    disease_date:   Optional[str]               = None
    medications:    Optional[List[MedicineSchema]] = None
    doctors_remark: Optional[str]               = None
    status:         Optional[PrescriptionStatus] = None


# ── Response schemas ─────────────────────────────────────

class PrescriptionResponseSchema(BaseModel):
    """Full prescription as stored in MongoDB, returned to the client."""
    id:             UUID
    patient_id:     UUID
    patient_name:   str
    disease_date:   str
    url:            Optional[str]       = None   # S3 URL; None until file is uploaded
    medications:    List[MedicineSchema]
    status:         PrescriptionStatus
    doctors_remark: Optional[str]       = None
    created_at:     datetime

    model_config = {"from_attributes": True}   # allows .model_validate(mongo_doc)


# ── Internal schema ────────────────

class PrescriptionInDBSchema(PrescriptionCreateSchema):
    """
    Extended schema used internally after the file is uploaded to S3.
    The router builds this from PrescriptionCreateSchema + the S3 URL,
    then serialises it for MongoDB.
    """
    id:         UUID     = Field(default_factory=uuid4)
    url:        Optional[str] = None              # populated after S3 upload
    created_at: datetime = Field(default_factory=datetime.now)