from fastapi import APIRouter
from fastapi import Depends

from fastapi import HTTPException

from app.database.models import User
from app.database.models import ChatSession
from app.auth.dependencies import get_current_app_user


from sqlalchemy.orm import Session

from app.database.session import (
    get_db
)

from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    CreateSessionResponse,
    ChatSessionSummary,
    MessageResponse,
    SessionSummaryResponse
)

from app.services.chat_service import (
    chat_service
)

router = APIRouter(
    tags=["Chat"]
)


@router.post(
    "/chat/session",
    response_model=CreateSessionResponse
)


async def create_session(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_app_user)
):
    session = await chat_service.create_session(
        db=db,
        user_id=user.id
    )

    previous_summary = await chat_service.get_latest_session_summary(
        db=db,
        user_id=user.id
    )

    return CreateSessionResponse(
        session_id=session.id,
        previous_session_summary=previous_summary.summary if previous_summary else None,
        previous_session_summary_created_at=previous_summary.created_at if previous_summary else None,
        previous_session_id=previous_summary.source_session_id if previous_summary else None
    )


@router.get(
    "/chat/sessions",
    response_model=list[ChatSessionSummary]
)
async def list_sessions(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_app_user)
):
    sessions = (
        db.query(ChatSession)
        .filter(
            ChatSession.user_id == user.id
        )
        .order_by(ChatSession.created_at.desc())
        .all()
    )

    session_ids = [session.id for session in sessions]
    message_counts = {}

    if session_ids:
        from sqlalchemy import func
        from app.database.models import ChatMessage

        counts = (
            db.query(
                ChatMessage.session_id,
                func.count(ChatMessage.id)
            )
            .filter(
                ChatMessage.session_id.in_(session_ids)
            )
            .group_by(ChatMessage.session_id)
            .all()
        )
        message_counts = {session_id: count for session_id, count in counts}

    return [
        ChatSessionSummary(
            id=session.id,
            status=session.status,
            created_at=session.created_at,
            message_count=message_counts.get(session.id, 0)
        )
        for session in sessions
    ]


@router.post(
    "/chat/message",
    response_model=ChatResponse
)
async def send_message(
    request: ChatRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_app_user)
):

    try:
        result = await chat_service.send_message(
            db=db,
            session_id=request.session_id,
            user_message=request.message,
            user_id=user.id,
            user_email=user.email
        )
    except Exception as ex:
        raise HTTPException(
            status_code=404,
            detail=str(ex)
        )

    return ChatResponse(
        session_id=request.session_id,
        response=result["response"],
        requires_approval=result["requires_approval"],
        approval_id=result["approval_id"],
        approval_user_email=result.get("approval_user_email")
    )


@router.get(
    "/chat/history/{session_id}",
    response_model=list[MessageResponse]
)
async def get_history(
    session_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_app_user)
):

    messages = await chat_service.get_history(
        db=db,
        session_id=session_id,
        user_id=user.id
    )

    return [
        {
            "role": m.role,
            "content": m.content,
            "created_at": m.created_at
        }
        for m in messages
    ]


@router.get(
    "/chat/summaries/latest",
    response_model=SessionSummaryResponse | None
)
async def latest_session_summary(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_app_user)
):
    summary = await chat_service.get_latest_session_summary(
        db=db,
        user_id=user.id
    )

    if not summary:
        return None

    return SessionSummaryResponse(
        session_id=summary.session_id,
        source_session_id=summary.source_session_id,
        summary=summary.summary,
        created_at=summary.created_at
    )


@router.get(
    "/chat/summaries/{session_id}",
    response_model=SessionSummaryResponse | None
)
async def session_summary(
    session_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_app_user)
):
    summary = await chat_service.get_session_summary(
        db=db,
        session_id=session_id,
        user_id=user.id
    )

    if not summary:
        return None

    return SessionSummaryResponse(
        session_id=summary.session_id,
        source_session_id=summary.source_session_id,
        summary=summary.summary,
        created_at=summary.created_at
    )
