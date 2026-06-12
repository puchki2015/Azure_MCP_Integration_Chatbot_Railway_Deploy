from fastapi import Depends
from fastapi import HTTPException
from fastapi.security import HTTPBearer
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.jwt_validator import JWTValidator
from app.config.settings import get_settings
from app.database.models import User
from app.database.session import get_db

security = HTTPBearer(auto_error=False)

validator = JWTValidator()
settings = get_settings()


async def get_current_user(
    credentials=Depends(security)
):
    if credentials is None:
        if settings.DEV_BYPASS_AUTH:
            return {
                "oid": "dev-bypass-oid",
                "sub": "dev-bypass-oid",
                "email": settings.DEV_BYPASS_USER_EMAIL.lower(),
                "preferred_username": settings.DEV_BYPASS_USER_EMAIL.lower(),
                "name": settings.DEV_BYPASS_USER_NAME
            }

        raise HTTPException(
            status_code=401,
            detail="Not authenticated"
        )

    try:

        payload = await validator.validate_token(
            credentials.credentials
        )

        return payload

    except Exception as ex:

        raise HTTPException(
            status_code=401,
            detail=f"Token validation failed: {ex}"
        )


def _allowed_emails() -> set[str]:
    return {
        email.strip().lower()
        for email in settings.ALLOWED_USER_EMAILS.split(",")
        if email.strip()
    }


def _admin_emails() -> set[str]:
    return {
        email.strip().lower()
        for email in settings.ADMIN_USER_EMAILS.split(",")
        if email.strip()
    }


def _claim_email(payload: dict) -> str | None:
    return (
        payload.get("preferred_username")
        or payload.get("email")
        or payload.get("upn")
        or payload.get("unique_name")
    )


async def get_current_app_user(
    payload: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> User:
    oid = payload.get("oid") or payload.get("sub")
    email = _claim_email(payload) or (f"{oid}@entra.local" if oid else None)

    if not oid or not email:
        raise HTTPException(
            status_code=401,
            detail="Token is missing required user identity claims"
        )

    normalized_email = email.lower()
    allowed = _allowed_emails()
    admins = _admin_emails()

    if allowed and normalized_email not in allowed:
        raise HTTPException(
            status_code=403,
            detail="User is not allowed to access this application"
        )

    user = (
        db.query(User)
        .filter(User.entra_oid == oid)
        .first()
    )

    if not user:
        user = (
            db.query(User)
            .filter(User.email == normalized_email)
            .first()
        )

    display_name = (
        payload.get("name")
        or payload.get("given_name")
        or normalized_email
    )

    if user:
        user.email = normalized_email
        user.display_name = display_name
    else:
        user = User(
            entra_oid=oid,
            email=normalized_email,
            display_name=display_name
        )
        db.add(user)

    user.is_admin = normalized_email in admins

    try:
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        user = (
            db.query(User)
            .filter(User.entra_oid == oid)
            .first()
        )

        if not user:
            raise

    return user
