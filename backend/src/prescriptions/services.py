from uuid import UUID, uuid4

from bson import Binary
from fastapi import HTTPException, UploadFile, status
import  os
from db.db import get_db
from storage.storage import upload_bytes

from .schemas import (
    PrescriptionCreateSchema,
    PrescriptionInDBSchema,
    PrescriptionResponseSchema,
    PrescriptionStatus,
    PrescriptionUpdateSchema,
)

S3_BUCKET     = os.getenv("S3_BUCKET_NAME")
ALLOWED_TYPES = {"application/pdf", "image/jpeg", "image/png", "image/webp"}
COLLECTION    = "prescriptions"


# ---------- helpers -----------------------------------------------------------

def _uuid_to_bin(uid: UUID) -> Binary:
    return Binary(uid.bytes, 3)


def _bin_to_uuid(val) -> UUID:
    """
    Safely convert whatever MongoDB gives back to a UUID.
    Covers three storage formats:
      - bson.Binary subtype 3  -> 16 raw bytes  -> UUID(bytes=...)
      - plain bytes (16 bytes) -> UUID(bytes=...)
      - plain string           -> UUID(str)
    """
    if isinstance(val, (bytes, Binary)):
        raw = bytes(val)          # bson.Binary.__bytes__ works in pymongo >= 3
        if len(raw) == 16:
            return UUID(bytes=raw)
        # edge-case: bytes that are actually an ASCII UUID string
        return UUID(raw.decode("ascii"))
    # already a string or something str()-able
    return UUID(str(val))


def _doc_to_response(doc: dict) -> PrescriptionResponseSchema:
    return PrescriptionResponseSchema(
        id=_bin_to_uuid(doc["_id"]),
        patient_id=_bin_to_uuid(doc["patient_id"]),
        patient_name=doc["patient_name"],
        disease_date=doc["disease_date"],
        url=doc.get("url"),
        medications=doc["medications"],
        status=doc["status"],
        doctors_remark=doc.get("doctors_remark"),
        created_at=doc["created_at"],
    )


async def _upload_to_s3(file: UploadFile, folder: str = "prescriptions") -> str:
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

async def add_prescription_service(
    payload: PrescriptionCreateSchema,
    file: UploadFile,
    current_user_id: UUID,
) -> PrescriptionResponseSchema:
    s3_url = await _upload_to_s3(file)

    db_doc   = PrescriptionInDBSchema(**payload.model_dump(), url=s3_url)
    document = db_doc.model_dump()
    document["_id"]        = _uuid_to_bin(db_doc.id)
    document["patient_id"] = _uuid_to_bin(db_doc.patient_id)
    del document["id"]

    db = get_db()
    db[COLLECTION].insert_one(document)

    return PrescriptionResponseSchema(**db_doc.model_dump())


def get_prescription_by_id_service(
    prescription_id: UUID,
    current_user_id: UUID,
) -> PrescriptionResponseSchema:
    db  = get_db()
    doc = db[COLLECTION].find_one({"_id": _uuid_to_bin(prescription_id)})

    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prescription not found.")

    if _bin_to_uuid(doc["patient_id"]) != current_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    return _doc_to_response(doc)


def get_all_my_prescriptions_service(
    current_user_id: UUID,
    prescription_status: PrescriptionStatus | None = None,
    skip: int = 0,
    limit: int = 20,
) -> list[PrescriptionResponseSchema]:
    db    = get_db()
    query = {"patient_id": _uuid_to_bin(current_user_id)}
    if prescription_status:
        query["status"] = prescription_status.value

    docs = (
        db[COLLECTION]
        .find(query)
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
    )

    return [_doc_to_response(doc) for doc in docs]


def update_prescription_service(
    prescription_id: UUID,
    payload: PrescriptionUpdateSchema,
    current_user_id: UUID,
) -> PrescriptionResponseSchema:
    db  = get_db()
    doc = db[COLLECTION].find_one({"_id": _uuid_to_bin(prescription_id)})

    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prescription not found.")

    if _bin_to_uuid(doc["patient_id"]) != current_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    updates = payload.model_dump(exclude_unset=True, exclude={"url"})
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update.")

    db[COLLECTION].update_one(
        {"_id": _uuid_to_bin(prescription_id)},
        {"$set": updates},
    )

    updated = db[COLLECTION].find_one({"_id": _uuid_to_bin(prescription_id)})
    return _doc_to_response(updated)


def delete_prescription_service(
    prescription_id: UUID,
    current_user_id: UUID,
) -> dict:
    db  = get_db()
    doc = db[COLLECTION].find_one({"_id": _uuid_to_bin(prescription_id)})

    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prescription not found.")

    if _bin_to_uuid(doc["patient_id"]) != current_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    db[COLLECTION].delete_one({"_id": _uuid_to_bin(prescription_id)})
    return {"detail": "Prescription deleted successfully."}