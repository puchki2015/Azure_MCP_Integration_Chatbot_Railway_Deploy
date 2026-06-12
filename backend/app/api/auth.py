from fastapi import APIRouter
from fastapi import Depends

from app.auth.dependencies import (
    get_current_app_user
)
from app.database.models import User
from app.schemas.auth import UserInfo

router = APIRouter()


@router.get(
    "/me",
    response_model=UserInfo
)

async def me(
    user: User = Depends(get_current_app_user)
):

    return UserInfo(
        oid=user.entra_oid,
        email=user.email,
        display_name=user.display_name,
        is_admin=getattr(user, "is_admin", False)
    )
