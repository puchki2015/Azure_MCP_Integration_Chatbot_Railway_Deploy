import asyncio
import json
import os
import sys
import unittest
from datetime import datetime
from unittest.mock import AsyncMock
from unittest.mock import patch
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("OPENAI_API_KEY", "test")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault(
    "ENTRA_TENANT_ID",
    "11111111-1111-1111-1111-111111111111"
)
os.environ.setdefault(
    "ENTRA_CLIENT_ID",
    "22222222-2222-2222-2222-222222222222"
)
os.environ.setdefault(
    "AZURE_TENANT_ID",
    "11111111-1111-1111-1111-111111111111"
)
os.environ.setdefault(
    "AZURE_CLIENT_ID",
    "33333333-3333-3333-3333-333333333333"
)
os.environ.setdefault("AZURE_CLIENT_SECRET", "secret")
os.environ.setdefault(
    "AZURE_SUBSCRIPTION_ID",
    "44444444-4444-4444-4444-444444444444"
)

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.database.base import Base
from app.database.models import ApprovalRequest
from app.database.models import ApprovalActionLog
from app.database.models import ChatSession
from app.database.models import ChatMessage
from app.database.models import SessionMemory
from app.database.models import User
from app.services.approval_executor import approval_executor
from app.services.mcp_command_registry import mcp_command_registry
from app.services.mcp_service import MCPPayloadError
from app.services.mcp_service import mcp_service
from app.schemas.tool_resolution import ToolResolution


class FakeTool:
    name = "arm"

    def __init__(self):
        self.received_args = None

    async def ainvoke(self, args):
        self.received_args = args
        return {
            "ok": True,
            "args": args
        }


class BackendContractTests(unittest.TestCase):

    def setUp(self):
        mcp_command_registry.registry = {
            "arm": {
                "create_or_update_resource_group": {
                    "required": ["request"],
                    "optional": [],
                    "parameters": {},
                    "destructive": True,
                    "read_only": False
                }
            }
        }

    def test_validate_payload_preserves_command_and_parameters(self):
        payload = {
            "command": "create_or_update_resource_group",
            "parameters": {
                "request": {
                    "resourceGroupName": "rg-test"
                }
            }
        }

        validated = mcp_service.validate_payload(
            tool_name="arm",
            payload=payload
        )

        self.assertEqual(validated, payload)

    def test_validate_payload_rejects_missing_required_parameter(self):
        payload = {
            "command": "create_or_update_resource_group",
            "parameters": {}
        }

        with self.assertRaises(MCPPayloadError):
            mcp_service.validate_payload(
                tool_name="arm",
                payload=payload
            )

    def test_call_tool_invokes_mcp_with_full_command_payload(self):
        fake_tool = FakeTool()
        payload = {
            "command": "create_or_update_resource_group",
            "parameters": {
                "request": {
                    "resourceGroupName": "rg-test"
                }
            }
        }

        async def run_test():
            with patch(
                "app.services.mcp_service.azure_mcp_client.get_tools",
                return_value=[fake_tool]
            ):
                result = await mcp_service.call_tool(
                    tool_name="arm",
                    payload=payload
                )

            self.assertEqual(fake_tool.received_args, payload)
            self.assertEqual(result["args"], payload)

        asyncio.run(run_test())

    def test_approval_executor_persists_execution_result(self):
        engine = create_engine("sqlite:///:memory:")
        TestingSession = sessionmaker(bind=engine)
        Base.metadata.create_all(bind=engine)

        db = TestingSession()
        user = User(
            entra_oid="oid-1",
            email="user@example.com",
            display_name="User"
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        session = ChatSession(user_id=user.id)
        db.add(session)
        db.commit()
        db.refresh(session)

        approval = ApprovalRequest(
            user_id=user.id,
            session_id=session.id,
            action="Create resource group",
            tool_name="arm",
            payload=json.dumps(
                {
                    "command": "create_or_update_resource_group",
                    "parameters": {
                        "request": {
                            "resourceGroupName": "rg-test"
                        }
                    }
                }
            ),
            status="APPROVED",
            approved=True,
            approved_by=user.email
        )
        db.add(approval)
        db.commit()
        db.refresh(approval)

        async def run_test():
            with patch(
                "app.services.approval_executor.mcp_service.call_tool",
                new=AsyncMock(return_value={"ok": True})
            ):
                result = await approval_executor.execute(
                    db=db,
                    approval_id=approval.id
                )

            db.refresh(approval)
            self.assertEqual(result, {"ok": True})
            self.assertEqual(approval.status, "EXECUTED")
            self.assertIn('"ok": true', approval.result)
            self.assertIsNone(approval.error_message)

        asyncio.run(run_test())
        db.close()
        engine.dispose()

    def test_approval_executor_marks_error_payload_as_failed(self):
        engine = create_engine("sqlite:///:memory:")
        TestingSession = sessionmaker(bind=engine)
        Base.metadata.create_all(bind=engine)

        db = TestingSession()
        user = User(
            entra_oid="oid-payload-error",
            email="payload.error@example.com",
            display_name="Payload Error User"
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        session = ChatSession(user_id=user.id)
        db.add(session)
        db.commit()
        db.refresh(session)

        approval = ApprovalRequest(
            user_id=user.id,
            session_id=session.id,
            action="Create resource group",
            tool_name="arm",
            payload=json.dumps(
                {
                    "command": "create_or_update_resource_group",
                    "parameters": {
                        "request": {
                            "resourceGroupName": "rg-test"
                        }
                    }
                }
            ),
            status="APPROVED",
            approved=True,
            approved_by=user.email
        )
        db.add(approval)
        db.commit()
        db.refresh(approval)

        async def run_test():
            with patch(
                "app.services.approval_executor.mcp_service.call_tool",
                new=AsyncMock(return_value=[
                    {
                        "type": "text",
                        "text": "An unexpected error occurred. To report this issue, visit https://aka.ms/ARMMCPIssue and provide the following trace ID: \"6973b79959249f5db9fddd47179bb1c9\".",
                        "id": "lc_dd826128-94fe-4e9c-a6f8-5ad4985911c8"
                    }
                ])
            ):
                with self.assertRaises(Exception):
                    await approval_executor.execute(
                        db=db,
                        approval_id=approval.id
                    )

            db.refresh(approval)
            self.assertEqual(approval.status, "FAILED")
            self.assertIn("unexpected error occurred", approval.error_message.lower())

        asyncio.run(run_test())
        db.close()
        engine.dispose()

    def test_approval_executor_marks_nested_json_error_payload_as_failed(self):
        engine = create_engine("sqlite:///:memory:")
        TestingSession = sessionmaker(bind=engine)
        Base.metadata.create_all(bind=engine)

        db = TestingSession()
        user = User(
            entra_oid="oid-nested-json-error",
            email="nested.json.error@example.com",
            display_name="Nested JSON Error User"
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        session = ChatSession(user_id=user.id)
        db.add(session)
        db.commit()
        db.refresh(session)

        approval = ApprovalRequest(
            user_id=user.id,
            session_id=session.id,
            action="Create storage account",
            tool_name="storage",
            payload=json.dumps(
                {
                    "command": "create_storage_account",
                    "parameters": {
                        "request": {
                            "resourceGroupName": "rg-storage"
                        }
                    }
                }
            ),
            status="APPROVED",
            approved=True,
            approved_by=user.email
        )
        db.add(approval)
        db.commit()
        db.refresh(approval)

        async def run_test():
            with patch(
                "app.services.approval_executor.mcp_service.call_tool",
                new=AsyncMock(return_value=[
                    {
                        "type": "text",
                        "text": "{\"status\":400,\"message\":\"Invalid storage SKU 'LRS'. Valid values are: Standard_LRS, Standard_GRS, Standard_RAGRS, Standard_ZRS, Premium_LRS, Premium_ZRS, Standard_GZRS, Standard_RAGZRS.. To mitigate this issue, please refer to the troubleshooting guidelines here at https://aka.ms/azmcp/troubleshooting.\",\"results\":{\"message\":\"Invalid storage SKU 'LRS'. Valid values are: Standard_LRS, Standard_GRS, Standard_RAGRS, Standard_ZRS, Premium_LRS, Premium_ZRS, Standard_GZRS, Standard_RAGZRS.\",\"type\":\"ArgumentException\"},\"duration\":0}",
                        "id": "lc_edc10504-1c9e-4b78-b626-ee3cf8dcd05a"
                    }
                ])
            ):
                with self.assertRaises(Exception):
                    await approval_executor.execute(
                        db=db,
                        approval_id=approval.id
                    )

            db.refresh(approval)
            self.assertEqual(approval.status, "FAILED")
            self.assertIn("Invalid storage SKU", approval.error_message or "")

        asyncio.run(run_test())
        db.close()
        engine.dispose()

    def test_openapi_schema_builds(self):
        from app.main import app
        from app.database.session import engine

        schema = app.openapi()

        self.assertIn("/api/v1/chat/message", schema["paths"])
        self.assertIn(
            "/api/v1/approvals/{approval_id}/approve",
            schema["paths"]
        )
        self.assertIn("HTTPBearer", schema["components"]["securitySchemes"])

        engine.dispose()

    def test_speech_token_endpoint_returns_backend_token(self):
        from app.api.speech import get_speech_token

        engine = create_engine("sqlite:///:memory:")
        TestingSession = sessionmaker(bind=engine)
        Base.metadata.create_all(bind=engine)

        db = TestingSession()
        user = User(
            entra_oid="oid-speech",
            email="speech@example.com",
            display_name="Speech User"
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        from app.config.settings import get_settings
        settings = get_settings()
        original_key = settings.AZURE_SPEECH_KEY
        original_region = settings.AZURE_SPEECH_REGION
        original_language = settings.AZURE_SPEECH_LANGUAGE

        class FakeResponse:
            def __init__(self):
                self.text = "speech-token-123"

            def raise_for_status(self):
                return None

        async def run_test():
            settings.AZURE_SPEECH_KEY = "speech-key"
            settings.AZURE_SPEECH_REGION = "eastus"
            settings.AZURE_SPEECH_LANGUAGE = "en-US"

            try:
                with patch(
                    "app.api.speech.httpx.Client.post",
                    return_value=FakeResponse()
                ) as post_mock:
                    result = get_speech_token(db=db, user=user)
            finally:
                settings.AZURE_SPEECH_KEY = original_key
                settings.AZURE_SPEECH_REGION = original_region
                settings.AZURE_SPEECH_LANGUAGE = original_language

            self.assertEqual(result.token, "speech-token-123")
            self.assertEqual(result.region, "eastus")
            self.assertEqual(result.language, "en-US")
            self.assertEqual(result.expires_in, 600)
            self.assertTrue(post_mock.called)

        asyncio.run(run_test())
        db.close()
        engine.dispose()

    def test_dev_bypass_auth_returns_mock_payload_without_bearer_token(self):
        from app.auth import dependencies as auth_dependencies
        from app.auth.dependencies import get_current_user

        original_bypass = auth_dependencies.settings.DEV_BYPASS_AUTH
        original_email = auth_dependencies.settings.DEV_BYPASS_USER_EMAIL
        original_name = auth_dependencies.settings.DEV_BYPASS_USER_NAME

        async def run_test():
            auth_dependencies.settings.DEV_BYPASS_AUTH = True
            auth_dependencies.settings.DEV_BYPASS_USER_EMAIL = "dev.user@example.com"
            auth_dependencies.settings.DEV_BYPASS_USER_NAME = "Dev User"

            try:
                payload = await get_current_user(credentials=None)
            finally:
                auth_dependencies.settings.DEV_BYPASS_AUTH = original_bypass
                auth_dependencies.settings.DEV_BYPASS_USER_EMAIL = original_email
                auth_dependencies.settings.DEV_BYPASS_USER_NAME = original_name

            self.assertEqual(payload["email"], "dev.user@example.com")
            self.assertEqual(payload["name"], "Dev User")
            self.assertEqual(payload["oid"], "dev-bypass-oid")

        asyncio.run(run_test())

    def test_chat_service_passes_recent_history_to_tool_resolver(self):
        from app.services.chat_service import chat_service

        engine = create_engine("sqlite:///:memory:")
        TestingSession = sessionmaker(bind=engine)
        Base.metadata.create_all(bind=engine)

        db = TestingSession()
        user = User(
            entra_oid="oid-history",
            email="history@example.com",
            display_name="History User"
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        session = ChatSession(user_id=user.id)
        db.add(session)
        db.commit()
        db.refresh(session)

        db.add_all([
            ChatMessage(
                session_id=session.id,
                role="user",
                content="create a resource group called prev-rg"
            ),
            ChatMessage(
                session_id=session.id,
                role="assistant",
                content="Your message requires approval. Approval ID: 7"
            )
        ])
        db.commit()

        async def run_test():
            with patch(
                "app.services.tool_resolver.tool_resolver.resolve",
                new=AsyncMock(
                    return_value=ToolResolution(
                        tool_name="arm",
                        payload={
                            "command": "create_or_update_resource_group",
                            "parameters": {
                                "request": {
                                    "scope": {
                                        "subscriptionId": "44444444-4444-4444-4444-444444444444"
                                    },
                                    "resourceGroupName": "history-rg",
                                    "definition": {
                                        "location": "eastus"
                                    }
                                }
                            }
                        },
                        requires_approval=False
                    )
                )
            ) as resolve_mock, patch(
                "app.agents.azure_agent.azure_agent.invoke",
                new=AsyncMock(return_value="ok")
            ):
                result = await chat_service.send_message(
                    db=db,
                    session_id=session.id,
                    user_message="use the same resource group called current-rg",
                    user_id=user.id
                )

            self.assertEqual(result["response"], "ok")
            self.assertFalse(result["requires_approval"])

            _, kwargs = resolve_mock.call_args
            history = kwargs["conversation_history"]

            self.assertGreaterEqual(len(history), 3)
            self.assertEqual(history[-1]["role"], "user")
            self.assertIn("current-rg", history[-1]["content"])
            self.assertIn("prev-rg", history[0]["content"])

        asyncio.run(run_test())
        db.close()
        engine.dispose()

    def test_new_session_carries_forward_previous_session_memory(self):
        from app.services.chat_service import chat_service

        engine = create_engine("sqlite:///:memory:")
        TestingSession = sessionmaker(bind=engine)
        Base.metadata.create_all(bind=engine)

        db = TestingSession()
        user = User(
            entra_oid="oid-memory",
            email="memory@example.com",
            display_name="Memory User"
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        previous_session = ChatSession(user_id=user.id)
        db.add(previous_session)
        db.commit()
        db.refresh(previous_session)

        db.add_all([
            ChatMessage(
                session_id=previous_session.id,
                role="user",
                content="create a resource group called memory-rg in east us"
            ),
            ChatMessage(
                session_id=previous_session.id,
                role="assistant",
                content="Your message requires approval. Approval ID: 9"
            )
        ])
        db.commit()

        async def run_test():
            with patch(
                "app.services.chat_service.chat_service._generate_session_summary",
                new=AsyncMock(return_value=(
                    "The user asked to create a resource group named memory-rg in east us, "
                    "and the assistant reported approval was required. The next session "
                    "should remember the resource group name, region, and approval context."
                ))
            ):
                current_session = await chat_service.create_session(
                    db=db,
                    user_id=user.id
                )

            memory = (
                db.query(SessionMemory)
                .filter(SessionMemory.session_id == current_session.id)
                .first()
            )

            self.assertIsNotNone(memory)
            self.assertIn("memory-rg", memory.summary)
            self.assertIn("east", memory.summary.lower())
            self.assertEqual(memory.source_session_id, previous_session.id)

            with patch(
                "app.services.tool_resolver.tool_resolver.resolve",
                new=AsyncMock(
                    return_value=ToolResolution(
                        tool_name="arm",
                        payload={
                            "command": "create_or_update_resource_group",
                            "parameters": {
                                "request": {
                                    "scope": {
                                        "subscriptionId": "44444444-4444-4444-4444-444444444444"
                                    },
                                    "resourceGroupName": "followup-rg",
                                    "definition": {
                                        "location": "eastus"
                                    }
                                }
                            }
                        },
                        requires_approval=False
                    )
                )
            ) as resolve_mock, patch(
                "app.agents.azure_agent.azure_agent.invoke",
                new=AsyncMock(return_value="ok")
            ):
                await chat_service.send_message(
                    db=db,
                    session_id=current_session.id,
                    user_message="use the same region as before and create followup-rg",
                    user_id=user.id
                )

            _, kwargs = resolve_mock.call_args
            history = kwargs["conversation_history"]
            self.assertEqual(history[0]["role"], "system")
            self.assertIn("memory-rg", history[0]["content"])
            self.assertIn("east", history[0]["content"].lower())

        asyncio.run(run_test())
        db.close()
        engine.dispose()

    def test_create_session_route_returns_previous_summary_fields(self):
        from app.api.chat import create_session

        engine = create_engine("sqlite:///:memory:")
        TestingSession = sessionmaker(bind=engine)
        Base.metadata.create_all(bind=engine)

        db = TestingSession()
        user = User(
            entra_oid="oid-route-summary",
            email="route.summary@example.com",
            display_name="Route Summary User"
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        fake_session = ChatSession(user_id=user.id)
        fake_session.id = 42
        fake_summary = SimpleNamespace(
            summary="User planned a resource group rollout in east us and needs the next session to remember it.",
            created_at=datetime(2026, 6, 10, 4, 0, 0),
            source_session_id=7
        )

        async def run_test():
            with patch(
                "app.api.chat.chat_service.create_session",
                new=AsyncMock(return_value=fake_session)
            ), patch(
                "app.api.chat.chat_service.get_latest_session_summary",
                new=AsyncMock(return_value=fake_summary)
            ):
                response = await create_session(db=db, user=user)

            self.assertEqual(response.session_id, 42)
            self.assertIn("east us", response.previous_session_summary)
            self.assertEqual(response.previous_session_summary_created_at, fake_summary.created_at)
            self.assertEqual(response.previous_session_id, 7)

        asyncio.run(run_test())
        db.close()
        engine.dispose()

    def test_registry_resolves_azure_cli_alias_to_registered_command(self):
        from app.services.mcp_command_registry import mcp_command_registry

        mcp_command_registry.registry = {
            "arm": {
                "create_or_update_resource_group": {
                    "required": ["request"],
                    "optional": [],
                    "parameters": {},
                    "destructive": True,
                    "read_only": False,
                    "description": "Creates or updates an Azure resource group"
                }
            }
        }

        self.assertEqual(
            mcp_command_registry.resolve_command_name(
                tool_name="arm",
                command_name="az group create"
            ),
            "create_or_update_resource_group"
        )

    def test_chat_sessions_endpoint_returns_user_sessions(self):
        from app.api.chat import list_sessions

        engine = create_engine("sqlite:///:memory:")
        TestingSession = sessionmaker(bind=engine)
        Base.metadata.create_all(bind=engine)

        db = TestingSession()
        user = User(
            entra_oid="oid-sessions",
            email="sessions@example.com",
            display_name="Sessions User"
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        session_one = ChatSession(user_id=user.id)
        session_two = ChatSession(user_id=user.id)
        db.add_all([session_one, session_two])
        db.commit()

        async def run_test():
            sessions = await list_sessions(db=db, user=user)
            self.assertEqual(len(sessions), 2)
            self.assertGreaterEqual(sessions[0].id, sessions[1].id)

        asyncio.run(run_test())
        db.close()
        engine.dispose()

    def test_approvals_endpoint_filters_by_status_and_scope(self):
        from app.api.approvals import list_pending_approvals

        engine = create_engine("sqlite:///:memory:")
        TestingSession = sessionmaker(bind=engine)
        Base.metadata.create_all(bind=engine)

        db = TestingSession()
        user = User(
            entra_oid="oid-admin",
            email="admin@example.com",
            display_name="Admin User"
        )
        user.is_admin = True
        db.add(user)
        db.commit()
        db.refresh(user)

        session = ChatSession(user_id=user.id)
        db.add(session)
        db.commit()
        db.refresh(session)

        db.add_all([
            ApprovalRequest(
                user_id=user.id,
                session_id=session.id,
                action="Pending request",
                tool_name="arm",
                payload=json.dumps({"command": "create_or_update_resource_group", "parameters": {"request": {"scope": {"subscriptionId": "44444444-4444-4444-4444-444444444444"}, "resourceGroupName": "rg", "definition": {"location": "eastus"}}}}),
                status="PENDING",
                approved=False
            ),
            ApprovalRequest(
                user_id=user.id,
                session_id=session.id,
                action="Approved request",
                tool_name="arm",
                payload=json.dumps({"command": "create_or_update_resource_group", "parameters": {"request": {"scope": {"subscriptionId": "44444444-4444-4444-4444-444444444444"}, "resourceGroupName": "rg2", "definition": {"location": "eastus"}}}}),
                status="APPROVED",
                approved=True
            ),
            ApprovalRequest(
                user_id=user.id,
                session_id=session.id,
                action="Failed request",
                tool_name="arm",
                payload=json.dumps({"command": "create_or_update_resource_group", "parameters": {"request": {"scope": {"subscriptionId": "44444444-4444-4444-4444-444444444444"}, "resourceGroupName": "rg3", "definition": {"location": "eastus"}}}}),
                status="FAILED",
                approved=True,
                error_message="ARM deployment failed"
            )
        ])
        db.commit()

        async def run_test():
            pending = await list_pending_approvals(db=db, user=user, status="PENDING", scope="all")
            approved = await list_pending_approvals(db=db, user=user, status="APPROVED", scope="all")
            failed = await list_pending_approvals(db=db, user=user, status="FAILED", scope="all")

            self.assertEqual(len(pending), 1)
            self.assertEqual(len(approved), 1)
            self.assertEqual(len(failed), 1)
            self.assertEqual(pending[0].status, "PENDING")
            self.assertEqual(approved[0].status, "APPROVED")
            self.assertEqual(failed[0].status, "FAILED")

        asyncio.run(run_test())
        db.close()
        engine.dispose()

    def test_approval_execution_failure_returns_structured_error(self):
        from app.api.approvals import approve_request

        engine = create_engine("sqlite:///:memory:")
        TestingSession = sessionmaker(bind=engine)
        Base.metadata.create_all(bind=engine)

        db = TestingSession()
        admin = User(
            entra_oid="oid-admin-failure",
            email="admin_anirban@anirbanazure01gmail.onmicrosoft.com",
            display_name="Admin User"
        )
        admin.is_admin = True
        user = User(
            entra_oid="oid-normal-failure",
            email="normal.failure@example.com",
            display_name="Normal User"
        )
        db.add_all([admin, user])
        db.commit()
        db.refresh(admin)
        db.refresh(user)

        session = ChatSession(user_id=user.id)
        db.add(session)
        db.commit()
        db.refresh(session)

        approval = ApprovalRequest(
            user_id=user.id,
            session_id=session.id,
            action="Need approval",
            tool_name="arm",
            payload=json.dumps({
                "command": "create_or_update_resource_group",
                "parameters": {
                    "request": {
                        "scope": {
                            "subscriptionId": "44444444-4444-4444-4444-444444444444"
                        },
                        "resourceGroupName": "rg-failure",
                        "definition": {
                            "location": "eastus"
                        }
                    }
                }
            }),
            status="PENDING",
            approved=False
        )
        db.add(approval)
        db.commit()
        db.refresh(approval)

        async def run_test():
            with patch(
                "app.services.approval_executor.mcp_service.call_tool",
                new=AsyncMock(side_effect=Exception("ARM deployment failed"))
            ):
                response = await approve_request(
                    approval_id=approval.id,
                    request=SimpleNamespace(reason="admin approved but execution failed"),
                    db=db,
                    user=admin
                )

            db.refresh(approval)
            self.assertEqual(response.status, "FAILED")
            self.assertIn("execution failed", response.message.lower())
            self.assertIn("ARM deployment failed", response.error_message)
            self.assertEqual(approval.status, "FAILED")
            self.assertEqual(approval.error_message, "ARM deployment failed")

            log_entry = (
                db.query(ApprovalActionLog)
                .filter(ApprovalActionLog.approval_id == approval.id)
                .first()
            )
            self.assertIsNotNone(log_entry)
            self.assertEqual(log_entry.status, "FAILED")
            self.assertEqual(log_entry.admin_email, admin.email)
            self.assertIn("ARM deployment failed", log_entry.error_message or "")

        asyncio.run(run_test())
        db.close()
        engine.dispose()

    def test_action_history_endpoint_includes_payload_and_result(self):
        from app.api.approvals import list_action_history

        engine = create_engine("sqlite:///:memory:")
        TestingSession = sessionmaker(bind=engine)
        Base.metadata.create_all(bind=engine)

        db = TestingSession()
        admin = User(
            entra_oid="oid-admin-history",
            email="admin_anirban@anirbanazure01gmail.onmicrosoft.com",
            display_name="Admin User"
        )
        admin.is_admin = True
        user = User(
            entra_oid="oid-normal-history",
            email="normal.history@example.com",
            display_name="Normal User"
        )
        db.add_all([admin, user])
        db.commit()
        db.refresh(admin)
        db.refresh(user)

        session = ChatSession(user_id=user.id)
        db.add(session)
        db.commit()
        db.refresh(session)

        approval = ApprovalRequest(
            user_id=user.id,
            session_id=session.id,
            action="Need approval",
            tool_name="arm",
            payload=json.dumps({
                "command": "create_or_update_resource_group",
                "parameters": {
                    "request": {
                        "scope": {
                            "subscriptionId": "44444444-4444-4444-4444-444444444444"
                        },
                        "resourceGroupName": "rg-history",
                        "definition": {
                            "location": "eastus"
                        }
                    }
                }
            }),
            status="FAILED",
            approved=True,
            error_message="ARM deployment failed"
        )
        db.add(approval)
        db.commit()
        db.refresh(approval)

        log_entry = ApprovalActionLog(
            approval_id=approval.id,
            admin_email=admin.email,
            action="APPROVE",
            status="FAILED",
            reason="test reason",
            result_text=None,
            error_message="ARM deployment failed"
        )
        db.add(log_entry)
        db.commit()

        async def run_test():
            history = await list_action_history(db=db, user=admin, scope="all", limit=10)
            self.assertEqual(len(history), 1)
            self.assertEqual(history[0]["approval_id"], approval.id)
            self.assertEqual(history[0]["tool_name"], "arm")
            self.assertEqual(history[0]["payload"]["parameters"]["request"]["resourceGroupName"], "rg-history")
            self.assertEqual(history[0]["error_message"], "ARM deployment failed")

        asyncio.run(run_test())
        db.close()
        engine.dispose()

    def test_approval_actions_are_admin_only(self):
        from app.api.approvals import approve_request
        from app.api.approvals import reject_request

        engine = create_engine("sqlite:///:memory:")
        TestingSession = sessionmaker(bind=engine)
        Base.metadata.create_all(bind=engine)

        db = TestingSession()
        admin = User(
            entra_oid="oid-admin-action",
            email="admin_anirban@anirbanazure01gmail.onmicrosoft.com",
            display_name="Admin User"
        )
        admin.is_admin = True
        user = User(
            entra_oid="oid-normal-action",
            email="normal@example.com",
            display_name="Normal User"
        )
        db.add_all([admin, user])
        db.commit()
        db.refresh(admin)
        db.refresh(user)

        session = ChatSession(user_id=user.id)
        db.add(session)
        db.commit()
        db.refresh(session)

        approval = ApprovalRequest(
            user_id=user.id,
            session_id=session.id,
            action="Need approval",
            tool_name="arm",
            payload=json.dumps({
                "command": "create_or_update_resource_group",
                "parameters": {
                    "request": {
                        "scope": {
                            "subscriptionId": "44444444-4444-4444-4444-444444444444"
                        },
                        "resourceGroupName": "rg-admin",
                        "definition": {
                            "location": "eastus"
                        }
                    }
                }
            }),
            status="PENDING",
            approved=False
        )
        db.add(approval)
        db.commit()
        db.refresh(approval)

        async def run_test():
            with self.assertRaises(Exception):
                await approve_request(
                    approval_id=approval.id,
                    request=SimpleNamespace(reason="nope"),
                    db=db,
                    user=user
                )

            with self.assertRaises(Exception):
                await reject_request(
                    approval_id=approval.id,
                    request=SimpleNamespace(reason="nope"),
                    db=db,
                    user=user
                )

            with patch(
                "app.api.approvals.approval_service.approve_request",
                new=AsyncMock(return_value=approval)
            ), patch(
                "app.api.approvals.approval_executor.execute",
                new=AsyncMock(return_value={"ok": True})
            ):
                approved = await approve_request(
                    approval_id=approval.id,
                    request=SimpleNamespace(reason="approved by admin"),
                    db=db,
                    user=admin
                )

            self.assertEqual(approved.status, "EXECUTED")

        asyncio.run(run_test())
        db.close()
        engine.dispose()


if __name__ == "__main__":
    unittest.main()
