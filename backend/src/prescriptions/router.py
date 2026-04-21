import json
from typing import Optional
from uuid import UUID

from fastapi import (APIRouter, Depends, File, Form, HTTPException,
                     Query, UploadFile, status)
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .schemas import (
    MedicineSchema,
    PrescriptionCreateSchema,
    PrescriptionResponseSchema,
    PrescriptionStatus,
    PrescriptionUpdateSchema,
)
from .services import (
    add_prescription_service,
    delete_prescription_service,
    get_all_my_prescriptions_service,
    get_prescription_by_id_service,
    update_prescription_service,
)

# ── JWT dependency ───────────────────────────────────────────────────────────────
# Replace the body of get_current_user with your actual JWT decode logic.
# The function must return the UUID that maps to patient_id in the DB.

import jwt
import os

bearer_scheme = HTTPBearer()

JWT_SECRET=os.getenv("JWT_SECRET")
JWT_ALGORITHM=os.getenv("JWT_ALGORITHM")

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> UUID:
    """
    Decode the Bearer JWT and return the user's UUID (maps to patient_id).
    Raises 401 if the token is missing, expired, or invalid.
    """
    try:
        token   = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise ValueError("No subject in token.")
        return UUID(user_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ── Router ───────────────────────────────────────────────────────────────────────

router = APIRouter(prefix="/api/prescriptions", tags=["Prescriptions"])


# POST /api/prescriptions/add
@router.post(
    "/add",
    response_model=PrescriptionResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new prescription with an attached file",
)
async def add_prescription(
    # ── multipart form fields ──────────────────────────────────────────────
    patient_id:          str           = Form(..., description="UUID of the patient"),
    patient_name:        str           = Form(...),
    disease_date:        str           = Form(..., description="Format: YYYY-MM-DD"),
    medications:         str           = Form(..., description='JSON array: [{"name":"...","dose":"...","frequency":"..."}]'),
    doctors_remark:      Optional[str] = Form(None),
    prescription_status: str           = Form("new"),

    # ── file ───────────────────────────────────────────────────────────────
    file: UploadFile = File(..., description="Prescription image or PDF"),

    # ── auth ───────────────────────────────────────────────────────────────
    current_user: UUID = Depends(get_current_user),
):
    """
    Upload a prescription along with its supporting document.
    The file is stored in S3; the resulting URL is saved in MongoDB.
    """
    try:
        meds = [MedicineSchema(**m) for m in json.loads(medications)]
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="'medications' must be a valid JSON array.",
        )

    payload = PrescriptionCreateSchema(
        patient_id=UUID(patient_id),
        patient_name=patient_name,
        disease_date=disease_date,
        medications=meds,
        doctors_remark=doctors_remark,
        status=PrescriptionStatus(prescription_status),
    )

    return await add_prescription_service(payload, file, current_user)


# GET /api/prescriptions/{prescription_id}
@router.get(
    "/{prescription_id}",
    response_model=PrescriptionResponseSchema,
    summary="Get a single prescription by ID",
)
async def get_prescription_by_id(
    prescription_id: UUID,
    current_user: UUID = Depends(get_current_user),
):
    """Fetch one prescription. Returns 403 if it does not belong to the requesting user."""
    return get_prescription_by_id_service(prescription_id, current_user)


# GET /api/prescriptions/
@router.get(
    "/",
    response_model=list[PrescriptionResponseSchema],
    summary="Get all prescriptions for the authenticated user",
)
async def get_all_my_prescriptions(
    prescription_status: Optional[PrescriptionStatus] = Query(
        None,
        alias="status",
        description="Filter by status: active | expired | new",
    ),
    skip:  int = Query(0,  ge=0,        description="Records to skip (pagination)"),
    limit: int = Query(20, ge=1, le=100, description="Max records to return"),
    current_user: UUID = Depends(get_current_user),
):
    """
    Returns all prescriptions whose patient_id matches the JWT user.
    Supports optional ?status= filter and skip/limit pagination.
    """
    return get_all_my_prescriptions_service(current_user, prescription_status, skip, limit)


# PUT /api/prescriptions/update/{prescription_id}
@router.put(
    "/update/{prescription_id}",
    response_model=PrescriptionResponseSchema,
    summary="Update a prescription (file/URL cannot be changed)",
)
async def update_prescription(
    prescription_id: UUID,
    payload: PrescriptionUpdateSchema,
    current_user: UUID = Depends(get_current_user),
):
    """
    Update editable fields of a prescription.
    The prescription file stored in S3 cannot be replaced via this endpoint.
    """
    return update_prescription_service(prescription_id, payload, current_user)


# DELETE /api/prescriptions/delete/{prescription_id}
@router.delete(
    "/delete/{prescription_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a prescription by ID",
)
async def delete_prescription(
    prescription_id: UUID,
    current_user: UUID = Depends(get_current_user),
):
    """Hard-delete a prescription. Only the owning patient can delete their own records."""
    return delete_prescription_service(prescription_id, current_user)