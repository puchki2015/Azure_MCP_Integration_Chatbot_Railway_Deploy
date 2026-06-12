import json

from sqlalchemy.orm import Session

from app.database.models import ApprovalRequest
from app.database.models import utc_now
from app.services.mcp_service import mcp_service


class ApprovalExecutor:

    def _parse_nested_json(self, value):
        if not isinstance(value, str):
            return value

        text = value.strip()
        if not text:
            return value

        if not (
            (text.startswith("{") and text.endswith("}"))
            or (text.startswith("[") and text.endswith("]"))
        ):
            return value

        try:
            return json.loads(text)
        except Exception:
            return value

    def _extract_tool_error_message(self, value) -> str | None:
        if value is None:
            return None

        if isinstance(value, str):
            parsed = self._parse_nested_json(value)
            if parsed is not value:
                return self._extract_tool_error_message(parsed)

            lowered = value.lower()
            if (
                "unexpected error occurred" in lowered
                or "trace id" in lowered
                or "invalid" in lowered
                or "failed" in lowered
                or "error" in lowered
            ):
                return value.strip()
            return None

        if isinstance(value, dict):
            status = value.get("status")
            if isinstance(status, int) and status >= 400:
                message = value.get("message") or value.get("error_message") or value.get("text")
                if isinstance(message, str) and message.strip():
                    return message.strip()
                return f"Tool returned error status {status}"

            for key in ("error_message", "error", "message", "text"):
                nested = value.get(key)
                if isinstance(nested, str):
                    parsed = self._parse_nested_json(nested)
                    if parsed is not nested:
                        nested_error = self._extract_tool_error_message(parsed)
                        if nested_error:
                            return nested_error

                    lowered = nested.lower()
                    if (
                        "unexpected error occurred" in lowered
                        or "trace id" in lowered
                        or "invalid" in lowered
                        or "failed" in lowered
                        or ("error" in lowered and "failed" in lowered)
                    ):
                        return nested.strip()

                nested_error = self._extract_tool_error_message(nested)
                if nested_error:
                    return nested_error
            return None

        if isinstance(value, list):
            for item in value:
                nested_error = self._extract_tool_error_message(item)
                if nested_error:
                    return nested_error
            return None

        return None

    def _is_error_result(self, result) -> tuple[bool, str | None]:
        error_message = self._extract_tool_error_message(result)
        return (error_message is not None, error_message)

    async def execute(
        self,
        db: Session,
        approval_id: int
    ):

        approval = (
            db.query(ApprovalRequest)
            .filter(
                ApprovalRequest.id == approval_id
            )
            .first()
        )

        if not approval:
            raise Exception(
                "Approval not found"
            )

        if approval.status != "APPROVED":
            raise Exception(
                f"Cannot execute approval in state {approval.status}"
            )

        try:
            payload = approval.payload

            if isinstance(payload, str):
                payload = json.loads(payload)

            result = await mcp_service.call_tool(
                tool_name=approval.tool_name,
                payload=payload
            )    

            is_error_result, error_message = self._is_error_result(result)
            if is_error_result:
                approval.status = "FAILED"
                approval.error_message = error_message
                approval.executed_at = utc_now()
                approval.result = json.dumps(
                    result,
                    default=str
                )
                db.commit()
                db.refresh(approval)
                raise Exception(error_message)

            approval.status = "EXECUTED"
            approval.executed_at = utc_now()
            approval.result = json.dumps(
                result,
                default=str
            )
            approval.error_message = None

            db.commit()
            db.refresh(approval)

            return result

        except Exception as ex:

            approval.status = "FAILED"
            approval.error_message = str(ex)
            approval.executed_at = utc_now()

            db.commit()

            raise ex


approval_executor = ApprovalExecutor()
