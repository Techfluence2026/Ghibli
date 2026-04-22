from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, status

from auth.router import get_current_user
from .schemas import (
    MedicationCreateSchema,
    MedicationResponseSchema,
    MedicationUpdateSchema,
)
from .services import (
    add_medication_service,
    delete_medication_service,
    get_all_my_medications_service,
    update_medication_service,
)

router = APIRouter(prefix="/api/medications", tags=["Medications"])


@router.post("/", response_model=MedicationResponseSchema, status_code=status.HTTP_201_CREATED)
def add_medication(
    payload: MedicationCreateSchema,
    current_user: UUID = Depends(get_current_user),
):
    return add_medication_service(payload, current_user)


@router.get("/", response_model=List[MedicationResponseSchema])
def get_all_my_medications(
    skip: int = 0,
    limit: int = 100,
    current_user: UUID = Depends(get_current_user),
):
    return get_all_my_medications_service(current_user, skip, limit)


@router.put("/{med_id}", response_model=MedicationResponseSchema)
def update_medication(
    med_id: UUID,
    payload: MedicationUpdateSchema,
    current_user: UUID = Depends(get_current_user),
):
    return update_medication_service(med_id, payload, current_user)


@router.delete("/{med_id}", status_code=status.HTTP_200_OK)
def delete_medication(
    med_id: UUID, current_user: UUID = Depends(get_current_user)
):
    return delete_medication_service(med_id, current_user)
