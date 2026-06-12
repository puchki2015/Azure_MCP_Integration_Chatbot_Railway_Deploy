import json

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_app_user
from app.database.models import ApprovalRequest
from app.database.models import ApprovalActionLog
from app.database.models import User
from app.database.session import get_db
from app.schemas.approval import (
    ApprovalActionResponse,
    ApprovalDecisionRequest,
    ApprovalResponse
)
from app.services.approval_executor import approval_executor
from app.services.approval_service import approval_service
from app.config.settings import get_settings

router = APIRouter(
    tags=["Approvals"]
)

settings = get_settings()


def _loads_payload(payload: str | dict) -> dict:
    if isinstance(payload, dict):
        return payload

    return json.loads(payload)


def _approval_to_response(
    approval: ApprovalRequest
) -> ApprovalResponse:
    return ApprovalResponse(
        id=approval.id,
        user_id=approval.user_id,
        user_email=getattr(getattr(approval, "user", None), "email", None),
        session_id=approval.session_id,
        action=approval.action,
        tool_name=approval.tool_name,
        payload=_loads_payload(approval.payload),
        status=approval.status,
        approved=approval.approved,
        approved_by=approval.approved_by,
        decision_reason=getattr(approval, "decision_reason", None),
        created_at=approval.created_at,
        approved_at=approval.approved_at,
        executed_at=approval.executed_at,
        error_message=approval.error_message
    )


def _action_log_to_response(
    log: ApprovalActionLog,
    approval: ApprovalRequest | None = None
) -> dict:
    return {
        "id": log.id,
        "approval_id": log.approval_id,
        "session_id": getattr(approval, "session_id", None),
        "admin_email": log.admin_email,
        "action": log.action,
        "status": log.status,
        "reason": log.reason,
        "tool_name": getattr(approval, "tool_name", None),
        "payload": _loads_payload(getattr(approval, "payload", "{}")),
        "result_text": log.result_text,
        "error_message": log.error_message,
        "created_at": log.created_at
    }


def _get_user_approval(
    db: Session,
    approval_id: int,
    user_id: int
) -> ApprovalRequest:
    approval = (
        db.query(ApprovalRequest)
        .filter(
            ApprovalRequest.id == approval_id,
            ApprovalRequest.user_id == user_id
        )
        .first()
    )

    if not approval:
        raise HTTPException(
            status_code=404,
            detail="Approval request not found"
        )

    return approval


def _admin_emails() -> set[str]:
    return {
        email.strip().lower()
        for email in settings.ADMIN_USER_EMAILS.split(",")
        if email.strip()
    }


def _is_admin(user: User) -> bool:
    return getattr(user, "is_admin", False) or user.email.lower() in _admin_emails()


def _normalize_status_filter(status: str) -> set[str]:
    normalized = status.upper()

    if normalized == "APPROVED":
        return {"APPROVED", "EXECUTED"}

    if normalized == "FAILED":
        return {"FAILED"}

    return {normalized}


@router.get(
    "/approvals",
    response_model=list[ApprovalResponse]
)
async def list_pending_approvals(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_app_user),
    status: str = Query("PENDING"),
    scope: str = Query("mine")
):
    normalized_status = status.upper()
    if normalized_status not in {"PENDING", "APPROVED", "REJECTED", "EXECUTED", "FAILED"}:
        raise HTTPException(
            status_code=400,
            detail="Invalid approval status"
        )

    is_admin = _is_admin(user)

    if scope == "all" and not is_admin:
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )

    query = db.query(ApprovalRequest).filter(
        ApprovalRequest.status.in_(_normalize_status_filter(normalized_status))
    )

    if scope != "all" or not is_admin:
        query = query.filter(
            ApprovalRequest.user_id == user.id
        )

    approvals = (
        query.order_by(ApprovalRequest.created_at.desc()).all()
    )

    return [
        _approval_to_response(approval)
        for approval in approvals
    ]


@router.get(
    "/approvals/action-history"
)
async def list_action_history(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_app_user),
    scope: str = Query("mine"),
    limit: int = Query(10, ge=1, le=50)
):
    is_admin = _is_admin(user)
    if scope == "all" and not is_admin:
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )

    query = (
        db.query(ApprovalActionLog, ApprovalRequest)
        .join(ApprovalRequest, ApprovalActionLog.approval_id == ApprovalRequest.id)
    )
    if scope != "all" or not is_admin:
        query = query.filter(ApprovalRequest.user_id == user.id)

    logs = query.order_by(ApprovalActionLog.created_at.desc()).limit(limit).all()
    return [
        _action_log_to_response(log, approval)
        for log, approval in logs
    ]


@router.post(
    "/approvals/{approval_id}/approve",
    response_model=ApprovalActionResponse
)
async def approve_request(
    approval_id: int,
    request: ApprovalDecisionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_app_user)
):
    if not _is_admin(user):
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )

    try:
        await approval_service.approve_request(
            db=db,
            approval_id=approval_id,
            approved_by=user.email,
            reason=request.reason
        )

        try:
            result = await approval_executor.execute(
                db=db,
                approval_id=approval_id
            )

            await approval_service.log_action(
                db=db,
                approval_id=approval_id,
                admin_email=user.email,
                action="APPROVE",
                status="EXECUTED",
                reason=request.reason,
                result_text=json.dumps(result, default=str)
            )

            return ApprovalActionResponse(
                approval_id=approval_id,
                status="EXECUTED",
                message="Approval approved and executed",
                reason=request.reason,
                result=result,
                error_message=None,
                user_email=getattr(user, "email", None)
            )
        except Exception as ex:
            failed_approval = (
                db.query(ApprovalRequest)
                .filter(
                    ApprovalRequest.id == approval_id
                )
                .first()
            )

            await approval_service.log_action(
                db=db,
                approval_id=approval_id,
                admin_email=user.email,
                action="APPROVE",
                status=getattr(failed_approval, "status", "FAILED"),
                reason=request.reason,
                result_text=None,
                error_message=getattr(
                    failed_approval,
                    "error_message",
                    None
                ) or str(ex)
            )

            return ApprovalActionResponse(
                approval_id=approval_id,
                status=getattr(failed_approval, "status", "FAILED"),
                message="Approval approved but execution failed",
                reason=request.reason,
                result=None,
                error_message=getattr(
                    failed_approval,
                    "error_message",
                    None
                ) or str(ex),
                user_email=getattr(user, "email", None)
            )

    except ValueError as ex:
        raise HTTPException(
            status_code=409,
            detail=str(ex)
        )


@router.post(
    "/approvals/{approval_id}/reject",
    response_model=ApprovalActionResponse
)
async def reject_request(
    approval_id: int,
    request: ApprovalDecisionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_app_user)
):
    if not _is_admin(user):
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )

    try:
        approval = await approval_service.reject_request(
            db=db,
            approval_id=approval_id
            ,
            approved_by=user.email,
            reason=request.reason
        )
    except ValueError as ex:
        raise HTTPException(
            status_code=409,
            detail=str(ex)
        )

    await approval_service.log_action(
        db=db,
        approval_id=approval.id,
        admin_email=user.email,
        action="REJECT",
        status=approval.status,
        reason=request.reason,
        result_text=None,
        error_message=None
    )

    return ApprovalActionResponse(
        approval_id=approval.id,
        status=approval.status,
        message="Approval rejected",
        reason=request.reason,
        user_email=getattr(user, "email", None)
    )
