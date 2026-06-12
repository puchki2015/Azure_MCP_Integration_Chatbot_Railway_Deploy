import json

from sqlalchemy.orm import Session

from app.database.models import (
    ApprovalRequest,
    ApprovalActionLog,
    utc_now
)
from app.services.mcp_service import mcp_service


class ApprovalService:

    async def create_request(
        self,
        db: Session,
        user_id: int | None,
        session_id: int,
        action: str,
        tool_name: str,
        payload: dict
    ):

        validated_payload = mcp_service.validate_payload(
            tool_name=tool_name,
            payload=payload
        )

        request = ApprovalRequest(
            user_id=user_id,
            session_id=session_id,
            action=action,
            tool_name=tool_name,
            payload=json.dumps(validated_payload),
            status="PENDING"
        )

        db.add(request)
        db.commit()
        db.refresh(request)

        return request
    



    async def approve_request(
        self,
        db: Session,
        approval_id: int,
        approved_by: str,
        reason: str | None = None
    ):
        request = (
            db.query(ApprovalRequest)
            .filter(
                ApprovalRequest.id == approval_id
            )
            .first()
        )

        if not request:
            return None

        if request.status != "PENDING":
            raise ValueError(
                f"Cannot approve request in state {request.status}"
            )
        
        request.status = "APPROVED"
        request.approved = True
        request.approved_by = approved_by
        request.decision_reason = reason
        request.approved_at = utc_now()

        db.commit()
        db.refresh(request)

        return request

    async def log_action(
        self,
        db: Session,
        approval_id: int,
        admin_email: str,
        action: str,
        status: str,
        reason: str | None = None,
        result_text: str | None = None,
        error_message: str | None = None
    ) -> ApprovalActionLog:
        log_entry = ApprovalActionLog(
            approval_id=approval_id,
            admin_email=admin_email,
            action=action,
            status=status,
            reason=reason,
            result_text=result_text,
            error_message=error_message
        )

        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)
        return log_entry

    async def reject_request(
        self,
        db: Session,
        approval_id: int,
        approved_by: str,
        reason: str | None = None
    ):
        request = (
            db.query(ApprovalRequest)
            .filter(
                ApprovalRequest.id == approval_id
            )
            .first()
        )

        if not request:
            return None

        if request.status not in {"PENDING", "APPROVED", "EXECUTED"}:
            raise ValueError(
                f"Cannot reject request in state {request.status}"
            )

        request.status = "REJECTED"
        request.approved = False
        request.approved_by = approved_by
        request.decision_reason = reason
        request.approved_at = utc_now()

        db.commit()
        db.refresh(request)

        return request


approval_service = ApprovalService()
