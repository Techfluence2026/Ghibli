from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["Users"])


@router.post("/auth/signin")
def signin():
    pass


@router.post("/auth/login")
def login():
    pass


@router.post("/auth/logout")
def logout():
    pass


@router.post("/tokens/renew")
def renew_access_token():
    pass


@router.post("/tokens/revoke")
def revoke_access_token():
    pass
