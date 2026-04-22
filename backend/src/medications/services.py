import os
from datetime import datetime, timezone
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import HTTPException, status
from twilio.rest import Client

from db.db import get_db
from .schemas import (
    MedicationCreateSchema,
    MedicationInDBSchema,
    MedicationResponseSchema,
    MedicationUpdateSchema,
)

def _get_twilio_client() -> tuple["Client | None", str]:
    """Read credentials fresh from env on every call — never cache at module level."""
    sid   = os.getenv("TWILIO_ACCOUNT_SID", "").strip().strip("'\"")
    token = os.getenv("TWILIO_AUTH_TOKEN", "").strip().strip("'\"")
    raw   = os.getenv("TWILIO_WHATSAPP_NUMBER", "+14155238886").strip().strip("'\"")
    from_number = raw if raw.startswith("whatsapp:") else f"whatsapp:{raw}"

    if sid and token:
        return Client(sid, token), from_number
    print("[Twilio] TWILIO_ACCOUNT_SID or TWILIO_AUTH_TOKEN not set — skipping.")
    return None, from_number


def _resolve_tz(tz_string: str | None) -> ZoneInfo:
    """Return a ZoneInfo for the given IANA tz string, falling back to DEFAULT_TIMEZONE."""
    default = os.getenv("DEFAULT_USER_TIMEZONE", "UTC")
    for candidate in (tz_string, default, "UTC"):
        if candidate:
            try:
                return ZoneInfo(candidate)
            except (ZoneInfoNotFoundError, KeyError):
                continue
    return ZoneInfo("UTC")


def _sanitize_phone(raw: str) -> str | None:
    """
    Normalise a phone number to E.164 format (+<digits>).
    Returns None if the result looks implausible (< 7 digits).
    """
    digits = "".join(c for c in raw if c.isdigit() or c == "+")
    # Remove any embedded '+' that isn't the leading one
    if digits.startswith("+"):
        digits = "+" + digits[1:].replace("+", "")
    else:
        digits = digits.replace("+", "")
        digits = "+" + digits

    # Sanity-check: E.164 is between 8 and 15 digits (excluding the '+')
    digit_count = sum(c.isdigit() for c in digits)
    if digit_count < 7 or digit_count > 15:
        return None
    return digits


# ---------------------------------------------------------------------------
# CRUD services
# ---------------------------------------------------------------------------

def add_medication_service(
    payload: MedicationCreateSchema, current_user_id: UUID
) -> MedicationResponseSchema:
    db = get_db()
    med_id = uuid4()

    med_doc = MedicationInDBSchema(
        id=med_id,
        user_id=current_user_id,
        name=payload.name,
        dose=payload.dose,
        times=payload.times,
    )

    db["medications"].insert_one(med_doc.model_dump(mode="json"))

    return MedicationResponseSchema(**med_doc.model_dump())


def get_all_my_medications_service(
    current_user_id: UUID, skip: int = 0, limit: int = 100
) -> list[MedicationResponseSchema]:
    db = get_db()

    cursor = (
        db["medications"]
        .find({"user_id": str(current_user_id)})
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
    )

    medications = []
    for doc in cursor:
        try:
            doc["id"] = UUID(doc["id"]) if isinstance(doc["id"], str) else doc["id"]
            doc["user_id"] = (
                UUID(doc["user_id"]) if isinstance(doc["user_id"], str) else doc["user_id"]
            )
            medications.append(MedicationResponseSchema(**doc))
        except Exception:
            continue

    return medications


def delete_medication_service(med_id: UUID, current_user_id: UUID):
    db = get_db()
    result = db["medications"].delete_one(
        {"id": str(med_id), "user_id": str(current_user_id)}
    )
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medication not found or unauthorized",
        )
    return {"message": "Medication deleted successfully"}


def update_medication_service(
    med_id: UUID, payload: MedicationUpdateSchema, current_user_id: UUID
) -> MedicationResponseSchema:
    db = get_db()

    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields provided to update")

    result = db["medications"].update_one(
        {"id": str(med_id), "user_id": str(current_user_id)}, {"$set": update_data}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Medication not found")

    updated_doc = db["medications"].find_one({"id": str(med_id)})
    updated_doc["id"] = UUID(updated_doc["id"])
    updated_doc["user_id"] = UUID(updated_doc["user_id"])

    return MedicationResponseSchema(**updated_doc)


# ---------------------------------------------------------------------------
# Scheduler job
# ---------------------------------------------------------------------------

def check_and_send_alerts():
    """
    Called by APScheduler every minute.

    For each medication whose `times` list contains the current HH:MM value
    *in the owning user's local timezone*, send a WhatsApp reminder via Twilio.

    Key fixes vs. the original implementation:
      1. Per-user timezone  — times stored as "HH:MM" are interpreted in the
         user's own timezone (stored as an IANA string on the user document,
         e.g. "Asia/Kolkata").  The old code hardcoded "America/New_York",
         which was wrong for every non-Eastern user.
      2. Deduplication guard — a sent-log keyed on (med_id, HH:MM, UTC-date)
         prevents double-sends if the scheduler fires twice in the same minute
         (e.g. on a rolling restart).
      3. Phone validation — numbers that cannot be normalised to a plausible
         E.164 string are skipped with a warning instead of causing a Twilio
         error at send time.
    """
    db = get_db()

    # UTC "wall clock" used only for the deduplication key date component.
    utc_now = datetime.now(timezone.utc)
    utc_date_str = utc_now.strftime("%Y-%m-%d")

    # Pull every medication; we'll filter by per-user local time below.
    # For large datasets consider grouping by user first to reduce user lookups.
    all_meds = list(db["medications"].find({}))
    if not all_meds:
        return

    twilio_client, from_number = _get_twilio_client()
    if not twilio_client:
        return  # message already printed inside _get_twilio_client

    # Cache user documents within this tick to avoid redundant DB round-trips
    # when a user has multiple medications due at the same time.
    user_cache: dict[str, dict] = {}

    for med in all_meds:
        user_id = med.get("user_id")
        if not user_id:
            continue

        # ------------------------------------------------------------------
        # 1. Resolve the user and their timezone
        # ------------------------------------------------------------------
        if user_id not in user_cache:
            user_cache[user_id] = db["users"].find_one({"id": user_id}) or {}
        user = user_cache[user_id]

        if not user:
            continue

        user_tz = _resolve_tz(user.get("timezone"))
        current_time_for_user = datetime.now(user_tz).strftime("%H:%M")

        # ------------------------------------------------------------------
        # 2. Check whether any of this medication's times match right now
        # ------------------------------------------------------------------
        med_times: list = med.get("times", [])
        if current_time_for_user not in med_times:
            continue

        # ------------------------------------------------------------------
        # 3. Deduplication — skip if we already sent this reminder today
        # ------------------------------------------------------------------
        med_id_str = str(med.get("id", ""))
        dedup_key = f"sent:{med_id_str}:{current_time_for_user}:{utc_date_str}"

        if db["reminder_log"].find_one({"key": dedup_key}):
            print(f"Duplicate suppressed: {dedup_key}")
            continue

        # ------------------------------------------------------------------
        # 4. Validate and normalise the phone number
        # ------------------------------------------------------------------
        raw_phone = user.get("phone", "")
        phone = _sanitize_phone(raw_phone)
        if not phone:
            print(
                f"Skipping med {med_id_str}: phone '{raw_phone}' could not be "
                "normalised to E.164."
            )
            continue

        to_number = f"whatsapp:{phone}"
        message_body = (
            f"MediSync Reminder 🕒\n"
            f"It's time to take your medication:\n\n"
            f"💊 *{med.get('name')}*\n"
            f"💧 Dose: {med.get('dose')}\n\n"
            f"Stay healthy!"
        )

        # ------------------------------------------------------------------
        # 5. Send via Twilio and record in the dedup log
        # ------------------------------------------------------------------
        try:
            message = twilio_client.messages.create(
                from_=from_number,
                body=message_body,
                to=to_number,
            )
            print(
                f"Sent reminder for med '{med_id_str}' to {to_number}. "
                f"SID: {message.sid}"
            )
            # Write dedup record — TTL index on `created_at` (48 h) keeps
            # the collection from growing unboundedly.  Create the index once:
            #   db.reminder_log.createIndex(
            #       { "created_at": 1 }, { expireAfterSeconds: 172800 }
            #   )
            db["reminder_log"].insert_one(
                {"key": dedup_key, "created_at": utc_now}
            )
        except Exception as exc:
            print(f"Failed to send Twilio message for med {med_id_str}: {exc}")