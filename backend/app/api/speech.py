from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from sqlalchemy.orm import Session
import httpx

from app.auth.dependencies import get_current_app_user
from app.config.settings import get_settings
from app.database.models import User
from app.database.session import get_db
from app.schemas.speech import SpeechTokenResponse

router = APIRouter(tags=["Speech"])
settings = get_settings()


@router.get("/speech/token", response_model=SpeechTokenResponse)
def get_speech_token(
    db: Session = Depends(get_db),  # noqa: ARG001
    user: User = Depends(get_current_app_user)  # noqa: ARG001
):
    if not settings.AZURE_SPEECH_KEY or not settings.AZURE_SPEECH_REGION:
        raise HTTPException(
            status_code=500,
            detail="Azure Speech is not configured"
        )

    url = (
        f"https://{settings.AZURE_SPEECH_REGION}"
        ".api.cognitive.microsoft.com/sts/v1.0/issueToken"
    )

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(
                url,
                headers={
                    "Ocp-Apim-Subscription-Key": settings.AZURE_SPEECH_KEY
                }
            )
            response.raise_for_status()
            token = response.text.strip()
    except httpx.HTTPStatusError as ex:
        raise HTTPException(
            status_code=502,
            detail=f"Azure Speech token request failed: {ex.response.text}"
        ) from ex
    except Exception as ex:
        raise HTTPException(
            status_code=502,
            detail=f"Azure Speech token request failed: {ex}"
        ) from ex

    return SpeechTokenResponse(
        token=token,
        region=settings.AZURE_SPEECH_REGION,
        language=settings.AZURE_SPEECH_LANGUAGE,
        expires_in=600
    )
