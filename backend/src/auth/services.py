import uuid
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from db.db import get_db

from .models import Session, User
from .schemas import (LoginRequest, LoginResponse, RenewAccessTokenRequest,
                      RenewAccessTokenResponse, SigninRequest, SigninResponse)

# -- Utils --
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


SECRET_KEY = "your-super-secret-key"  # Ideally should be loaded from env vars
ALGORITHM = "HS256"


def create_token(user_id: str, email: str, expires_delta: timedelta):
    expire = datetime.utcnow() + expires_delta
    token_id = str(uuid.uuid4())
    payload = {
        "jti": token_id,
        "sub": str(user_id),
        "email": email,
        "exp": expire,
        "iat": datetime.utcnow(),
    }
    encoded_jwt = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt, payload


def verify_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise ValueError("Unable to verifying token")


# -- Services --


def signin_service(request: SigninRequest) -> SigninResponse:
    db = get_db()

    # Hash password
    try:
        hashed_password = hash_password(request.password)
    except Exception as e:
        print(e)
        raise ValueError("Error creating user")

    user_id = uuid.uuid4()

    user_doc = {
        "_id": str(user_id),
        "id": str(user_id),
        "username": request.username,
        "email": request.email,
        "password": hashed_password,
        "phone": request.phone,
    }

    try:
        db["users"].insert_one(user_doc)
    except Exception as e:
        print(e)
        raise ValueError("Error creating user")

    return SigninResponse(
        id=user_id,
        username=request.username,
        email=request.email,
        phone=request.phone,
    )


def login_service(request: LoginRequest) -> LoginResponse:
    db = get_db()

    # 1. Get user by email
    user_doc = db["users"].find_one({"email": request.email})
    if not user_doc:
        raise ValueError("User not found")

    # 2. Check password
    if not verify_password(request.password, user_doc.get("password")):
        raise ValueError("Invalid password")

    # 3. Create access and refresh tokens
    try:
        acc_token, acc_payload = create_token(
            user_doc.get("id"), user_doc.get("email"), timedelta(minutes=15)
        )
        ref_token, ref_payload = create_token(
            user_doc.get("id"), user_doc.get("email"), timedelta(hours=24)
        )
    except Exception:
        raise ValueError("Error creating token")

    # 4. Create Session
    session = Session()
    session.id = uuid.UUID(ref_payload["jti"])
    session.user_email = user_doc["email"]
    session.refresh_token = ref_token
    session.is_revoked = False
    session.expires_at = ref_payload["exp"]

    try:
        db["sessions"].insert_one(
            {
                "_id": str(session.id),
                "id": str(session.id),
                "user_email": session.user_email,
                "refresh_token": session.refresh_token,
                "is_revoked": session.is_revoked,
                "expires_at": session.expires_at,
            }
        )
    except Exception:
        raise ValueError("Unable to create session")

    user = User()
    try:
        user.id = uuid.UUID(user_doc.get("id"))
    except (ValueError, AttributeError):
        user.id = user_doc.get("id")
    user.email = user_doc.get("email", "")
    user.username = user_doc.get("username", "")
    user.phone = user_doc.get("phone", "")
    user.age = user_doc.get("age", 0)
    user.blood_group = user_doc.get("blood_group", "")
    user.diseases = user_doc.get("diseases", [])
    user.allergies = user_doc.get("allergies", [])
    user.height = user_doc.get("height", 0.0)
    user.weight = user_doc.get("weight", 0.0)
    user.gender = user_doc.get("gender", "")

    return LoginResponse(
        session_id=str(session.id),
        access_token=acc_token,
        access_token_expires_at=acc_payload["exp"],
        refresh_token=ref_token,
        refresh_token_expires_at=ref_payload["exp"],
        user=user,
    )


def logout_service(session_id: str):
    db = get_db()

    session_doc = db["sessions"].find_one({"id": session_id})
    if not session_doc:
        raise ValueError("Session not found")

    result = db["sessions"].delete_one({"id": session_id})
    if result.deleted_count == 0:
        raise ValueError("Unable to delete session")


def renew_access_token_service(
    request: RenewAccessTokenRequest,
) -> RenewAccessTokenResponse:
    db = get_db()

    # 1. Verify refresh token
    try:
        payload = verify_token(request.refresh_token)
    except ValueError:
        raise ValueError("Unable to verifying token")

    session_id = payload.get("jti")

    # 2. Get session
    session_doc = db["sessions"].find_one({"id": session_id})
    if not session_doc:
        raise ValueError("Session not found")

    # 3. Check session status
    if session_doc.get("is_revoked"):
        raise ValueError("Session is revoked")

    if session_doc.get("user_email") != payload.get("email"):
        raise ValueError("Invalid session")

    # 4. Create new access token
    try:
        acc_token, acc_payload = create_token(
            payload.get("sub"), payload.get("email"), timedelta(minutes=15)
        )
    except Exception:
        raise ValueError("Error creating access token")

    return RenewAccessTokenResponse(
        access_token=acc_token, access_token_expires_at=acc_payload["exp"]
    )


def revoke_access_token_service(session_id: str):
    db = get_db()

    session_doc = db["sessions"].find_one({"id": session_id})
    if not session_doc:
        raise ValueError("Unable to find session")

    result = db["sessions"].update_one(
        {"id": session_id}, {"$set": {"is_revoked": True}}
    )
    if result.matched_count == 0:
        raise ValueError("Unable to revoke session")
