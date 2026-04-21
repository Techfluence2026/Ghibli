from fastapi import APIRouter, Response, HTTPException, status

from db.db import get_db
from .schemas import (
    SigninRequest, SigninResponse,
    LoginRequest, LoginResponse,
    RenewAccessTokenRequest, RenewAccessTokenResponse
)
from .services import (
    signin_service, login_service, logout_service,
    renew_access_token_service, revoke_access_token_service
)

router = APIRouter(prefix="/api", tags=["Users"])


@router.post("/auth/signin", response_model=SigninResponse)
def signin(request: SigninRequest):
    try:
        return signin_service(request)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/auth/login", response_model=LoginResponse)
def login(request: LoginRequest):
    try:
        return login_service(request)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(id: str):
    try:
        logout_service(id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/tokens/renew", response_model=RenewAccessTokenResponse)
def renew_access_token(request: RenewAccessTokenRequest):
    try:
        return renew_access_token_service(request)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.post("/tokens/revoke", status_code=status.HTTP_204_NO_CONTENT)
def revoke_access_token(id: str):
    try:
        revoke_access_token_service(id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except ValueError as e:
        if "find" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
