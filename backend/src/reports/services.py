from uuid import UUID, uuid4

from bson import Binary
from fastapi import HTTPException, UploadFile, status

from db.db import get_db
from storage.storage import upload_bytes

from .schemas import (
    ReportCreateSchema,
    ReportInDBSchema,
    ReportResponseSchema,
    ReportStatus,
    ReportUpdateSchema,
)
import os

S3_BUCKET     = os.getenv("S3_BUCKET_NAME")
ALLOWED_TYPES = {"application/pdf", "image/jpeg", "image/png", "image/webp"}
COLLECTION    = "reports"


# ---------- helpers -----------------------------------------------------------

def _uuid_to_bin(uid: UUID) -> Binary:
    return Binary(uid.bytes, 3)


def _bin_to_uuid(val) -> UUID:
    if isinstance(val, (bytes, Binary)):
        raw = bytes(val)
        if len(raw) == 16:
            return UUID(bytes=raw)
        return UUID(raw.decode("ascii"))
    return UUID(str(val))


def _doc_to_response(doc: dict) -> ReportResponseSchema:
    return ReportResponseSchema(
        id=_bin_to_uuid(doc["_id"]),
        patient_id=_bin_to_uuid(doc["patient_id"]),
        patient_name=doc["patient_name"],
        url=doc.get("url"),
        tests=doc["tests"],
        doctor=doc["doctor"],
        lab_no=doc["lab_no"],
        status=doc["status"],
        created_at=doc["created_at"],
    )


async def _upload_to_s3(file: UploadFile, folder: str = "reports") -> str:
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"File type '{file.content_type}' not allowed. Use PDF or image.",
        )
    file_bytes = await file.read()
    ext    = file.filename.rsplit(".", 1)[-1] if "." in file.filename else "bin"
    s3_key = f"{folder}/{uuid4()}.{ext}"
    try:
        return upload_bytes(
            data=file_bytes,
            s3_key=s3_key,
            bucket=S3_BUCKET,
            content_type=file.content_type,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"S3 upload failed: {str(e)}",
        )


# ---------- services ----------------------------------------------------------

async def add_report_service(
    payload: ReportCreateSchema,
    file: UploadFile,
    current_user_id: UUID,
) -> ReportResponseSchema:
    s3_url = await _upload_to_s3(file)

    db_doc   = ReportInDBSchema(**payload.model_dump(), url=s3_url)
    document = db_doc.model_dump()
    document["_id"]        = _uuid_to_bin(db_doc.id)
    document["patient_id"] = _uuid_to_bin(db_doc.patient_id)
    del document["id"]

    db = get_db()
    db[COLLECTION].insert_one(document)

    return ReportResponseSchema(**db_doc.model_dump())


def get_report_by_id_service(
    report_id: UUID,
    current_user_id: UUID,
) -> ReportResponseSchema:
    db  = get_db()
    doc = db[COLLECTION].find_one({"_id": _uuid_to_bin(report_id)})

    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found.")

    if _bin_to_uuid(doc["patient_id"]) != current_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    return _doc_to_response(doc)


def get_all_my_reports_service(
    current_user_id: UUID,
    report_status: ReportStatus | None = None,
    skip: int = 0,
    limit: int = 20,
) -> list[ReportResponseSchema]:
    db    = get_db()
    query = {"patient_id": _uuid_to_bin(current_user_id)}
    if report_status:
        query["status"] = report_status.value

    docs = (
        db[COLLECTION]
        .find(query)
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
    )

    return [_doc_to_response(doc) for doc in docs]


def update_report_service(
    report_id: UUID,
    payload: ReportUpdateSchema,
    current_user_id: UUID,
) -> ReportResponseSchema:
    db  = get_db()
    doc = db[COLLECTION].find_one({"_id": _uuid_to_bin(report_id)})

    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found.")

    if _bin_to_uuid(doc["patient_id"]) != current_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    updates = payload.model_dump(exclude_unset=True, exclude={"url"})
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update.")

    db[COLLECTION].update_one(
        {"_id": _uuid_to_bin(report_id)},
        {"$set": updates},
    )

    updated = db[COLLECTION].find_one({"_id": _uuid_to_bin(report_id)})
    return _doc_to_response(updated)


def delete_report_service(
    report_id: UUID,
    current_user_id: UUID,
) -> dict:
    db  = get_db()
    doc = db[COLLECTION].find_one({"_id": _uuid_to_bin(report_id)})

    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found.")

    if _bin_to_uuid(doc["patient_id"]) != current_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    db[COLLECTION].delete_one({"_id": _uuid_to_bin(report_id)})
    return {"detail": "Report deleted successfully."}