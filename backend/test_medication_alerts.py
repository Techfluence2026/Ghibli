"""
test_medication_alerts.py
─────────────────────────
Standalone debug script for medication reminders & Twilio.

Run from the backend root:
    cd /path/to/MediSync/backend
    python test_medication_alerts.py

It does NOT need the FastAPI app to be running — it talks to MongoDB and
Twilio directly, the same way services.py does inside the scheduler.

Required env vars (already in your .env):
    MONGO_URL, MONGO_DB_NAME,
    TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_NUMBER

Optional env vars:
    TEST_PHONE_OVERRIDE   – send the test message to this number instead of
                            whatever is stored in the DB  (e.g. +918669829701)
    TEST_TIMEZONE_OVERRIDE – force a timezone for the test run (e.g. Asia/Kolkata)
"""

import os
import sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

# ── 0. Load .env ───────────────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))
except ImportError:
    # parse manually if python-dotenv isn't installed
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        for line in open(env_path):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

# ── helpers shared with services.py ───────────────────────────────────────────

def _get_twilio_client():
    sid       = os.getenv("TWILIO_ACCOUNT_SID", "").strip().strip("'\"")
    token     = os.getenv("TWILIO_AUTH_TOKEN",  "").strip().strip("'\"")
    raw       = os.getenv("TWILIO_WHATSAPP_NUMBER", "+14155238886").strip().strip("'\"")
    from_num  = raw if raw.startswith("whatsapp:") else f"whatsapp:{raw}"

    if sid and token:
        from twilio.rest import Client
        return Client(sid, token), from_num
    return None, from_num


def _resolve_tz(tz_str):
    override = os.getenv("TEST_TIMEZONE_OVERRIDE")
    default  = os.getenv("DEFAULT_USER_TIMEZONE", "UTC")
    for candidate in (override, tz_str, default, "UTC"):
        if candidate:
            try:
                return ZoneInfo(candidate)
            except (ZoneInfoNotFoundError, KeyError):
                continue
    return ZoneInfo("UTC")


def _sanitize_phone(raw: str):
    digits = "".join(c for c in raw if c.isdigit() or c == "+")
    if digits.startswith("+"):
        digits = "+" + digits[1:].replace("+", "")
    else:
        digits = "+" + digits.replace("+", "")
    digit_count = sum(c.isdigit() for c in digits)
    return digits if 7 <= digit_count <= 15 else None


# ── 1. Check env vars ─────────────────────────────────────────────────────────
print("=" * 60)
print("STEP 1 — ENV VARS")
print("=" * 60)
sid   = os.getenv("TWILIO_ACCOUNT_SID", "")
token = os.getenv("TWILIO_AUTH_TOKEN", "")
raw_from = os.getenv("TWILIO_WHATSAPP_NUMBER", "")
mongo_url = os.getenv("MONGO_URL", "")
db_name   = os.getenv("MONGO_DB_NAME", "mediDB")

print(f"  MONGO_URL              : {'SET' if mongo_url else '❌ MISSING'}")
print(f"  TWILIO_ACCOUNT_SID     : {'SET (' + sid[:6] + '...)' if sid else '❌ MISSING'}")
print(f"  TWILIO_AUTH_TOKEN      : {'SET' if token else '❌ MISSING'}")
print(f"  TWILIO_WHATSAPP_NUMBER : {repr(raw_from)}")
print(f"  TEST_PHONE_OVERRIDE    : {repr(os.getenv('TEST_PHONE_OVERRIDE', ''))}")
print(f"  TEST_TIMEZONE_OVERRIDE : {repr(os.getenv('TEST_TIMEZONE_OVERRIDE', ''))}")

if not all([sid, token, raw_from, mongo_url]):
    print("\n[FATAL] Missing required env vars. Aborting.")
    sys.exit(1)

# ── 2. Twilio auth ────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("STEP 2 — TWILIO AUTHENTICATION")
print("=" * 60)
twilio_client, from_number = _get_twilio_client()
if not twilio_client:
    print("  ❌ Could not create Twilio client. Check SID / token.")
    sys.exit(1)
try:
    acct = twilio_client.api.accounts(sid).fetch()
    print(f"  ✓ Authenticated as: {acct.friendly_name!r}  (status={acct.status})")
except Exception as e:
    print(f"  ❌ Auth test failed: {e}")
    sys.exit(1)
print(f"  From number: {from_number}")

# ── 3. MongoDB connection ─────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("STEP 3 — MONGODB CONNECTION")
print("=" * 60)
try:
    from pymongo import MongoClient
    mc  = MongoClient(mongo_url)
    db  = mc[db_name]
    mc.admin.command("ping")
    print(f"  ✓ Connected to MongoDB ({db_name})")
except Exception as e:
    print(f"  ❌ MongoDB connection failed: {e}")
    sys.exit(1)

# ── 4. Inspect medications collection ────────────────────────────────────────
print("\n" + "=" * 60)
print("STEP 4 — MEDICATIONS IN DB")
print("=" * 60)
meds = list(db["medications"].find({}))
print(f"  Found {len(meds)} medication(s):")
for m in meds:
    print(f"    • {m.get('name')} | dose={m.get('dose')} | times={m.get('times')} | user_id={m.get('user_id')}")

# ── 5. Per-user timezone resolution & time matching ───────────────────────────
print("\n" + "=" * 60)
print("STEP 5 — TIMEZONE RESOLUTION & TIME MATCHING")
print("=" * 60)
utc_now = datetime.now(timezone.utc)
print(f"  Current UTC time: {utc_now.strftime('%H:%M')} ({utc_now.isoformat()})")

matched = []
user_cache = {}
for m in meds:
    user_id = m.get("user_id")
    if not user_id:
        continue
    if user_id not in user_cache:
        user_cache[user_id] = db["users"].find_one({"id": user_id}) or {}
    user = user_cache[user_id]
    if not user:
        print(f"  ⚠  Med '{m.get('name')}': user {user_id} NOT found in DB!")
        continue

    saved_tz  = user.get("timezone")
    user_tz   = _resolve_tz(saved_tz)
    local_now = datetime.now(user_tz).strftime("%H:%M")
    med_times = m.get("times", [])

    status_icon = "✓" if local_now in med_times else "✗"
    tz_note     = f"(saved in DB)" if saved_tz else f"(⚠ no timezone saved — fell back)"
    print(
        f"  {status_icon}  Med '{m.get('name')}' | "
        f"tz={user_tz.key} {tz_note} | "
        f"local_now={local_now} | times={med_times}"
    )
    if local_now in med_times:
        matched.append((m, user, from_number))

# ── 6. Phone number validation ────────────────────────────────────────────────
print("\n" + "=" * 60)
print("STEP 6 — PHONE NUMBER VALIDATION")
print("=" * 60)
for user_id, user in user_cache.items():
    raw_phone = user.get("phone", "")
    clean     = _sanitize_phone(raw_phone)
    override  = os.getenv("TEST_PHONE_OVERRIDE", "")
    icon = "✓" if clean else "❌"
    print(
        f"  {icon}  user {user_id} | raw='{raw_phone}' → E.164={repr(clean)}"
        + (f"  [OVERRIDE → {override}]" if override else "")
    )

# ── 7. Send a forced test message (ignores time matching) ─────────────────────
print("\n" + "=" * 60)
print("STEP 7 — FORCE SEND TEST MESSAGE")
print("=" * 60)
phone_override = os.getenv("TEST_PHONE_OVERRIDE", "").strip()

if not phone_override:
    # Try the first user in the cache
    first_user = next(iter(user_cache.values()), {})
    phone_override = _sanitize_phone(first_user.get("phone", "") or "")
    if not phone_override:
        print("  ⚠  No TEST_PHONE_OVERRIDE set and no valid phone in DB — skipping send.")
        phone_override = None

if phone_override:
    to_number = phone_override if phone_override.startswith("whatsapp:") else f"whatsapp:{phone_override}"
    print(f"  Sending test message from {from_number} → {to_number} …")
    try:
        msg = twilio_client.messages.create(
            from_=from_number,
            to=to_number,
            body=(
                "MediSync DEBUG ✅\n"
                "If you see this, Twilio is configured correctly and the "
                "scheduler can reach your number.\n"
                f"Server UTC time: {utc_now.strftime('%H:%M')}"
            ),
        )
        print(f"  ✓ Message dispatched!")
        print(f"    SID    : {msg.sid}")
        print(f"    Status : {msg.status}")
        if msg.error_code:
            print(f"    Error  : {msg.error_code} / {msg.error_message}")
    except Exception as e:
        print(f"  ❌ Send failed: {e}")

# ── 8. Summary ────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
print(f"  Total medications   : {len(meds)}")
print(f"  Matched right now   : {len(matched)}")
if matched:
    print("  Would have sent to:")
    for med, user, _ in matched:
        print(f"    • {med.get('name')} → {user.get('phone')}")
else:
    print("  No medications match the current time.")
    print("  → Check that your Profile timezone is saved, or set TEST_TIMEZONE_OVERRIDE.")
