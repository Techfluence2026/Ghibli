import json
from typing import Optional
from uuid import UUID

from fastapi import (APIRouter, Depends, File, Form, HTTPException,
                     Query, UploadFile, status)
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import os
from .schemas import (
    ReportCreateSchema,
    ReportResponseSchema,
    ReportStatus,
    ReportUpdateSchema,
    TestSchema,
)
from .services import (
    add_report_service,
    delete_report_service,
    get_all_my_reports_service,
    get_report_by_id_service,
    update_report_service,
)

import jwt

bearer_scheme = HTTPBearer()

JWT_SECRET=os.getenv("JWT_SECRET")
JWT_ALGORITHM=os.getenv("JWT_ALGORITHM")

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> UUID:
    try:
        payload = jwt.decode(
            credentials.credentials,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
        )
        user_id = payload.get("sub")
        if not user_id:
            raise ValueError
        return UUID(user_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        )


router = APIRouter(prefix="/api/reports", tags=["Reports"])


# POST /api/reports/add
@router.post(
    "/add",
    response_model=ReportResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def add_report(
    patient_id:   str           = Form(...),
    patient_name: str           = Form(...),
    tests:        str           = Form(..., description='JSON: [{"name":"","result":"","unit":"","reference_range":""}]'),
    doctor:       str           = Form(...),
    lab_no:       str           = Form(...),
    report_status: str          = Form("pending"),
    file: UploadFile            = File(..., description="Lab report PDF or image"),
    current_user: UUID          = Depends(get_current_user),
):
    try:
        tests_list = [TestSchema(**t) for t in json.loads(tests)]
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="'tests' must be a valid JSON array.",
        )

    payload = ReportCreateSchema(
        patient_id=UUID(patient_id),
        patient_name=patient_name,
        tests=tests_list,
        doctor=doctor,
        lab_no=lab_no,
        status=ReportStatus(report_status),
    )

    return await add_report_service(payload, file, current_user)


# GET /api/reports/{report_id}
@router.get("/{report_id}", response_model=ReportResponseSchema)
def get_report_by_id(
    report_id: UUID,
    current_user: UUID = Depends(get_current_user),
):
    return get_report_by_id_service(report_id, current_user)


# GET /api/reports/
@router.get("/", response_model=list[ReportResponseSchema])
def get_all_my_reports(
    report_status: Optional[ReportStatus] = Query(
        None, alias="status", description="pending | reviewed | archived"
    ),
    skip:  int = Query(0,  ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: UUID = Depends(get_current_user),
):
    return get_all_my_reports_service(current_user, report_status, skip, limit)


# PUT /api/reports/update/{report_id}
@router.put("/update/{report_id}", response_model=ReportResponseSchema)
def update_report(
    report_id: UUID,
    payload: ReportUpdateSchema,
    current_user: UUID = Depends(get_current_user),
):
    return update_report_service(report_id, payload, current_user)


# DELETE /api/reports/delete/{report_id}
@router.delete("/delete/{report_id}", status_code=status.HTTP_200_OK)
def delete_report(
    report_id: UUID,
    current_user: UUID = Depends(get_current_user),
):
    return delete_report_service(report_id, current_user)