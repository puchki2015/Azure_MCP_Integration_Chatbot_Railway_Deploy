from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from textwrap import dedent
from zipfile import ZIP_DEFLATED, ZipFile
from xml.sax.saxutils import escape


OUT = Path(r"C:\Users\agniv\OneDrive\Desktop\azure_mcp_intr_codex\Azure_AI_Ops_Architecture_and_Business_Guide.docx")

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
P_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
DCT_NS = "http://purl.org/dc/terms/"
CP_NS = "http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
DC_NS = "http://purl.org/dc/elements/1.1/"
XML_NS = "http://www.w3.org/XML/1998/namespace"


def w(tag: str) -> str:
    return f"{{{W_NS}}}{tag}"


def xml_escape(text: str) -> str:
    return escape(text, {'"': "&quot;", "'": "&apos;"})


def p(text: str = "", *, style: str | None = None, align: str | None = None, bold: bool = False,
      italic: bool = False, size: int | None = None, color: str | None = None,
      caps: bool = False, spacing_before: int | None = None, spacing_after: int | None = None,
      keep_next: bool = False, page_break_before: bool = False) -> str:
    attrs = []
    if style:
        attrs.append(f'<w:pStyle w:val="{style}"/>')
    if align:
        attrs.append(f'<w:jc w:val="{align}"/>')
    if keep_next:
        attrs.append('<w:keepNext/>')
    if page_break_before:
        attrs.append('<w:pageBreakBefore/>')
    if spacing_before is not None or spacing_after is not None:
        spacing_bits = []
        if spacing_before is not None:
            spacing_bits.append(f'w:before="{spacing_before}"')
        if spacing_after is not None:
            spacing_bits.append(f'w:after="{spacing_after}"')
        attrs.append(f'<w:spacing {" ".join(spacing_bits)}/>')
    rpr = []
    if bold:
        rpr.append('<w:b/>')
    if italic:
        rpr.append('<w:i/>')
    if caps:
        rpr.append('<w:caps/>')
    if size is not None:
        rpr.append(f'<w:sz w:val="{size}"/>')
        rpr.append(f'<w:szCs w:val="{size}"/>')
    if color is not None:
        rpr.append(f'<w:color w:val="{color}"/>')
    if rpr:
        rpr_xml = f"<w:rPr>{''.join(rpr)}</w:rPr>"
    else:
        rpr_xml = ""
    return (
        f"<w:p>"
        f"{''.join(f'<w:pPr>{''.join(attrs)}</w:pPr>' if attrs else '')}"
        f"<w:r>{rpr_xml}<w:t xml:space=\"preserve\">{xml_escape(text)}</w:t></w:r>"
        f"</w:p>"
    )


def bullet(text: str, level: int = 0) -> str:
    indent = 720 * level
    return (
        "<w:p>"
        f"<w:pPr><w:ind w:left=\"{indent}\" w:hanging=\"360\"/><w:numPr><w:ilvl w:val=\"{level}\"/><w:numId w:val=\"1\"/></w:numPr></w:pPr>"
        f"<w:r><w:t xml:space=\"preserve\">{xml_escape(text)}</w:t></w:r>"
        "</w:p>"
    )


def numbered(text: str, level: int = 0) -> str:
    indent = 720 * level
    return (
        "<w:p>"
        f"<w:pPr><w:ind w:left=\"{indent}\" w:hanging=\"360\"/><w:numPr><w:ilvl w:val=\"{level}\"/><w:numId w:val=\"2\"/></w:numPr></w:pPr>"
        f"<w:r><w:t xml:space=\"preserve\">{xml_escape(text)}</w:t></w:r>"
        "</w:p>"
    )


def table(headers: list[str], rows: list[list[str]], widths: list[int] | None = None) -> str:
    def tc(text: str, shaded: bool = False) -> str:
        shading = '<w:shd w:fill="1F4E78"/>' if shaded else ''
        return (
            "<w:tc>"
            "<w:tcPr>"
            f"{shading}"
            "<w:tcMar><w:top w:w=\"80\" w:type=\"dxa\"/><w:left w:w=\"80\" w:type=\"dxa\"/>"
            "<w:bottom w:w=\"80\" w:type=\"dxa\"/><w:right w:w=\"80\" w:type=\"dxa\"/></w:tcMar>"
            "</w:tcPr>"
            f"<w:p><w:r>{'<w:rPr><w:b/><w:color w:val=\"FFFFFF\"/><w:sz w:val=\"20\"/><w:szCs w:val=\"20\"/></w:rPr>' if shaded else ''}<w:t xml:space=\"preserve\">{xml_escape(text)}</w:t></w:r></w:p>"
            "</w:tc>"
        )

    rows_xml = []
    header_cells = [tc(h, shaded=True) for h in headers]
    rows_xml.append(f"<w:tr>{''.join(header_cells)}</w:tr>")
    for row in rows:
        cells = [tc(val, shaded=False) for val in row]
        rows_xml.append(f"<w:tr>{''.join(cells)}</w:tr>")

    grid = "".join(f'<w:gridCol w:w="{w}"/>' for w in (widths or [2500] * len(headers)))
    return (
        "<w:tbl>"
        "<w:tblPr><w:tblStyle w:val=\"TableGrid\"/><w:tblW w:w=\"0\" w:type=\"auto\"/></w:tblPr>"
        f"<w:tblGrid>{grid}</w:tblGrid>"
        f"{''.join(rows_xml)}"
        "</w:tbl>"
    )


def paragraph_with_label(label: str, value: str) -> str:
    return (
        "<w:p>"
        f"<w:r><w:rPr><w:b/></w:rPr><w:t xml:space=\"preserve\">{xml_escape(label)}</w:t></w:r>"
        f"<w:r><w:t xml:space=\"preserve\">{xml_escape(value)}</w:t></w:r>"
        "</w:p>"
    )


def build_document_body() -> str:
    parts: list[str] = []
    parts.append(p("Azure AI Ops Platform", align="center", bold=True, size=44, color="1F4E78", spacing_after=60))
    parts.append(p("Architecture, Design Flow, Components, and Business Value", align="center", italic=True, size=24, color="44546A", spacing_after=40))
    parts.append(p("Technical and business reference guide for the current implementation", align="center", size=20, color="44546A", spacing_after=120))

    parts.append(table(
        ["Document scope", "What this guide covers"],
        [[
            "Current codebase",
            "FastAPI backend, React frontend, Microsoft Entra authentication, PostgreSQL, Redis, Docker Compose, Azure resource orchestration, approvals, voice input, operational logs, and business value."
        ]],
        widths=[3200, 7600]
    ))

    parts.append(p("1. Executive Summary", style="Heading1", bold=True, size=28, color="1F4E78", spacing_before=120, spacing_after=40))
    parts.append(p(
        "This application is an Azure operations assistant. Users sign in with Microsoft Entra ID, ask for infrastructure changes in natural language, and the backend converts the request into controlled Azure/MCP actions. Destructive or sensitive operations are routed through an approval workflow so business controls remain in place. The platform records sessions, approvals, decision reasons, execution results, failures, and action history for traceability.",
        size=20, spacing_after=80
    ))

    parts.append(p("2. Architecture Overview", style="Heading1", bold=True, size=28, color="1F4E78", spacing_before=120, spacing_after=40))
    parts.append(p(
        "The system follows a layered client-server architecture. The browser hosts the React UI. FastAPI is the orchestration layer and security boundary. PostgreSQL stores user, chat, approval, and action history data. Redis supports session/checkpoint state. Azure provides authentication, resource management, and speech services. Docker Compose packages the full stack for repeatable local execution.",
        size=20, spacing_after=60
    ))
    parts.append(table(
        ["Layer", "Primary responsibility", "Representative files"],
        [
            ["Presentation", "Login, chat, approvals, admin pages, voice input", "frontend/src/App.tsx; frontend/src/features/*; frontend/src/components/*"],
            ["API / orchestration", "Auth, chat routing, approvals, speech token issuance", "backend/app/main.py; backend/app/api/*.py"],
            ["Domain logic", "Tool resolution, approval execution, session memory, model routing", "backend/app/services/*.py; backend/app/agents/azure_agent.py"],
            ["Security", "Entra token validation, admin/user gating, allow-listing", "backend/app/auth/*.py"],
            ["Persistence", "Users, sessions, messages, approvals, summaries, logs", "backend/app/database/*.py"],
            ["Infrastructure", "Containerized app composition and ports", "docker-compose.yml; backend/Dockerfile; frontend/Dockerfile"],
        ],
        widths=[2200, 3600, 4600]
    ))

    parts.append(p("3. End-to-End Design Flow", style="Heading1", bold=True, size=28, color="1F4E78", spacing_before=120, spacing_after=40))
    flow = [
        "The user opens the React frontend and clicks Sign in with Microsoft.",
        "MSAL initiates Microsoft Entra sign-in using the frontend SPA app registration.",
        "After authentication, the frontend requests an access token for the backend API scope.",
        "The browser calls FastAPI endpoints with the bearer token in the Authorization header.",
        "FastAPI validates issuer, audience, and claims, then loads or creates the user record.",
        "A chat session is created, and the UI shows the chat area, history, approvals, and optional voice input.",
        "When the user submits a request, the backend resolves the command, checks history and memory, and decides whether the action needs approval.",
        "If approval is required, the request is stored as PENDING and surfaced to the user and admin views.",
        "Admins review the queue, add a mandatory reason, and approve or reject the request.",
        "Approval execution runs the Azure/MCP action. Success, failure, and tool error payloads are recorded.",
        "The UI receives the result and updates the approvals history, status, and action log panels.",
    ]
    parts.extend(numbered(x) for x in flow)

    parts.append(p("4. Components Involved and Their Roles", style="Heading1", bold=True, size=28, color="1F4E78", spacing_before=120, spacing_after=40))
    parts.append(table(
        ["Component", "Role in the system", "Why it matters"],
        [
            ["React frontend", "Handles login, chat UX, approvals pages, admin actions, voice input", "Keeps the user experience responsive and task focused"],
            ["FastAPI backend", "Validates auth, exposes APIs, orchestrates chat and approvals", "Acts as the security and control boundary"],
            ["Azure Agent / LangGraph", "Runs the tool-using assistant loop for Azure operations", "Performs reasoning and connects user intent to actions"],
            ["Tool resolver", "Chooses the right tool family and command", "Prevents the model from executing arbitrary commands"],
            ["Approval service", "Creates, lists, updates, and audits approvals", "Implements governance for sensitive operations"],
            ["Approval executor", "Runs approved Azure/MCP actions and classifies failures", "Ensures approved work is executed and tracked correctly"],
            ["MCP service and registry", "Resolves and invokes registered Azure commands", "Provides the execution bridge to Azure operations"],
            ["Microsoft Entra ID", "Authenticates users and issues access tokens", "Protects the platform and establishes identity"],
            ["PostgreSQL", "Stores users, chats, approvals, summaries, logs", "Provides durable auditability and reporting"],
            ["Redis", "Supports transient state and runtime coordination", "Improves responsiveness and service coordination"],
            ["Azure Speech", "Converts spoken input to text", "Enables voice-driven request entry"],
        ],
        widths=[2200, 3600, 3600]
    ))

    parts.append(p("5. Key Files and Why They Matter", style="Heading1", bold=True, size=28, color="1F4E78", spacing_before=120, spacing_after=40))
    parts.append(p("The following files are the main operational anchors of the project. This is not every file in the repository, but it covers the ones that drive behavior, security, and deployment.", size=20, spacing_after=40))
    parts.append(table(
        ["File or folder", "Importance"],
        [
            ["backend/app/main.py", "Application bootstrap; wires routers, CORS, schema init, and runtime setup."],
            ["backend/app/api/auth.py", "Returns the signed-in user profile and app-level identity data."],
            ["backend/app/api/chat.py", "Chat session creation, message handling, and history endpoints."],
            ["backend/app/api/approvals.py", "Approval queue, admin actions, status transitions, and audit views."],
            ["backend/app/api/speech.py", "Issues short-lived Azure Speech tokens for browser speech-to-text."],
            ["backend/app/auth/dependencies.py", "Enforces authentication and admin authorization."],
            ["backend/app/auth/jwt_validator.py", "Validates Microsoft Entra tokens against issuer and audience."],
            ["backend/app/agents/azure_agent.py", "Main reasoning and tool execution path for Azure operations."],
            ["backend/app/services/chat_service.py", "Coordinates session memory, summaries, planning, and response shaping."],
            ["backend/app/services/tool_resolver.py", "Selects the right tool family and command with lower token cost."],
            ["backend/app/services/approval_service.py", "Creates and updates approval records and action history."],
            ["backend/app/services/approval_executor.py", "Executes approved actions and classifies error payloads correctly."],
            ["backend/app/services/mcp_service.py", "Invokes MCP-registered Azure commands."],
            ["backend/app/services/mcp_command_registry.py", "Maps natural-language command names and aliases to actual tools."],
            ["backend/app/database/models.py", "Defines persistent data models for users, sessions, approvals, summaries, logs."],
            ["backend/app/config/settings.py", "Centralizes environment-driven configuration and model selection."],
            ["backend/app/schemas/*.py", "Defines API request and response contracts."],
            ["backend/tests/test_backend_contracts.py", "Regression tests for auth, approvals, execution, and API contracts."],
            ["frontend/src/App.tsx", "Top-level route composition and page wiring."],
            ["frontend/src/app/providers/AuthProvider.tsx", "Manages Entra login state and token acquisition."],
            ["frontend/src/services/msal.ts", "MSAL configuration for the frontend Entra app registration."],
            ["frontend/src/services/api.ts", "Shared API client and bearer-token handling."],
            ["frontend/src/features/chat/ChatPage.tsx", "Chat UX, session summary card, approvals entry point, voice input."],
            ["frontend/src/features/approvals/*", "User and admin approvals dashboards, action history, drawers, status views."],
            ["frontend/src/components/voice/*", "Browser microphone capture and speech-to-text integration."],
            ["frontend/src/styles/globals.css", "Visual design tokens and page-level styling."],
            ["frontend/Dockerfile and frontend/nginx.conf", "Frontend build and SPA routing in the container."],
            ["backend/Dockerfile", "Backend container build and dependency installation."],
            ["docker-compose.yml", "Defines the full local stack and service wiring."],
        ],
        widths=[3600, 7200]
    ))

    parts.append(p("6. Azure and Local Resources Used", style="Heading1", bold=True, size=28, color="1F4E78", spacing_before=120, spacing_after=40))
    parts.append(p("The app relies on a mix of Azure services and local containerized infrastructure.", size=20, spacing_after=40))
    parts.append(table(
        ["Resource", "Purpose", "Configuration location"],
        [
            ["Microsoft Entra ID app registration for the frontend", "Signs users in from the browser and requests access tokens", "frontend/.env and Entra portal"],
            ["Microsoft Entra ID app registration for the backend API", "Represents the protected API audience", "backend/.env and Entra portal"],
            ["Azure AI Speech resource", "Speech-to-text token issuance and recognition support", "backend/.env"],
            ["Azure subscription", "Target scope for ARM operations such as resource groups and storage", "backend/.env"],
            ["Azure client credentials", "Used by the backend Azure integration layer", "backend/.env"],
            ["PostgreSQL", "Persistent application data store", "docker-compose.yml"],
            ["Redis", "Runtime coordination / transient state", "docker-compose.yml"],
            ["Docker network and volumes", "Repeatable local execution and state persistence", "docker-compose.yml"],
        ],
        widths=[3200, 4200, 2800]
    ))
    parts.append(p("Important note: secret values such as client secrets and speech keys must remain in environment files and should not be hard-coded into the source tree or shared in documentation.", size=20, spacing_after=60))

    parts.append(p("7. Docker Compose Explained", style="Heading1", bold=True, size=28, color="1F4E78", spacing_before=120, spacing_after=40))
    parts.append(p("Docker Compose is the simplest way to run the entire platform locally. It defines the backend, frontend, PostgreSQL, and Redis as coordinated services.", size=20, spacing_after=40))
    parts.append(table(
        ["Service", "Image / build", "Ports", "Role"],
        [
            ["backend", "Builds from ./backend", "8000:8000", "Serves FastAPI APIs and Azure orchestration"],
            ["frontend", "Builds from ./frontend", "3000:80", "Serves the React app behind nginx"],
            ["postgres", "postgres:17", "5432:5432", "Stores users, sessions, approvals, histories, and logs"],
            ["redis", "redis:8", "6379:6379", "Supports transient state and coordination"],
        ],
        widths=[1400, 2200, 1400, 6000]
    ))
    for btxt in [
        "backend starts after PostgreSQL and Redis because it depends on them.",
        "frontend starts after backend so the UI can call the live APIs.",
        "backend/.env supplies identity, Azure, and speech settings to the API container.",
        "frontend builds the React app and serves it through nginx for SPA routing.",
        "PostgreSQL persistence survives container restarts because it uses a named volume.",
    ]:
        parts.append(bullet(btxt))

    parts.append(p("8. Step-by-Step Execution Guidance", style="Heading1", bold=True, size=28, color="1F4E78", spacing_before=120, spacing_after=40))
    steps = [
        "Build and start the stack with Docker Compose. This creates the backend, frontend, PostgreSQL, and Redis containers.",
        "Open the frontend in the browser at http://localhost:3000 when using Docker Compose.",
        "Sign in with Microsoft Entra ID. The frontend uses the SPA app registration and obtains a bearer token for the backend API.",
        "The chat landing page loads the current session, session summary, approvals entry card, and history sidebar.",
        "Type or speak a question. For voice input, the browser sends microphone audio to Azure Speech through the backend-issued short-lived speech token.",
        "The backend creates or reuses a chat session, then runs the planner and execution model split to decide whether the request can proceed or needs approval.",
        "If approval is required, the request enters the pending queue and is visible to both the user and the admin portal according to role-based access rules.",
        "The admin opens the approvals page, adds a mandatory reason, and approves or rejects the request.",
        "The backend executes the approved action. Success, failure, and tool error payloads are recorded in the database and shown in the UI.",
        "Action history and detailed drawers allow the admin to inspect what was decided and what the backend returned without leaving the page.",
    ]
    parts.extend(numbered(s) for s in steps)

    parts.append(p("9. Voice Mode of Communication", style="Heading1", bold=True, size=28, color="1F4E78", spacing_before=120, spacing_after=40))
    parts.append(p("Voice input is implemented as a frontend convenience layer over the existing chat pipeline. The user clicks the microphone button, grants browser permission, and speaks a question. The frontend sends the audio to Azure Speech using a short-lived token minted by the backend. The transcript is inserted into the same chat input box used for typing, so the user can review and edit it before sending.", size=20, spacing_after=40))
    for item in [
        "Speech-to-text only: this implementation captures spoken questions and converts them into text.",
        "Language: the configured speech locale is en-US.",
        "Security model: the speech key stays on the backend; the browser receives only a temporary token.",
        "User control: speech output is not automatic; the user still chooses when to send the request.",
        "Integration scope: voice input feeds the same chat and approval workflow, so no separate backend path is needed.",
    ]:
        parts.append(bullet(item))
    parts.append(p("Why this matters: voice input lowers friction for business users who prefer speaking over typing, and it makes the application more accessible without changing the underlying governance model.", size=20, spacing_after=60))

    parts.append(p("10. Challenges Encountered and How They Were Resolved", style="Heading1", bold=True, size=28, color="1F4E78", spacing_before=120, spacing_after=40))
    parts.append(table(
        ["Challenge", "Observed impact", "Resolution"],
        [
            ["OpenAI TPM rate limits", "Planner and agent calls hit token-per-minute limits on some requests", "Split the model usage by task: smaller models for planning and summarization, stronger model only for execution"],
            ["Tool payloads that returned error text instead of raising exceptions", "Failed actions were being marked as success", "Added error detection for plain-text and nested JSON failure payloads"],
            ["Frontend callback 404 in Docker", "Entra redirect route was not served as SPA", "Added nginx SPA fallback routing"],
            ["CORS preflight 405", "Browser OPTIONS requests were rejected before auth flow completed", "Enabled backend CORS middleware"],
            ["Token audience mismatch", "Valid Entra tokens were rejected with 401", "Accepted both GUID and api:// audience formats"],
            ["Missing email claim in some tokens", "User mapping rejected otherwise valid logins", "Added fallback claim mapping from preferred_username/upn/unique_name"],
            ["Docker pip download interruption", "Backend image build failed during dependency installation", "Hardened pip install retries and timeout settings"],
            ["Session memory too narrow", "New sessions could not recall prior context", "Added session summaries and carry-forward context"],
        ],
        widths=[2600, 3200, 4400]
    ))
    parts.append(p("The most important operational lesson was that the system should not use the same heavy model for every stage. Planning, summarization, and final execution have different cost and quality requirements. The code now reflects that split.", size=20, spacing_after=60))

    parts.append(p("11. Business Value for Users and Stakeholders", style="Heading1", bold=True, size=28, color="1F4E78", spacing_before=120, spacing_after=40))
    parts.append(p("This platform gives business and operations teams a controlled way to request cloud changes in plain English while preserving approvals, audit history, and execution accountability. It reduces friction between requesters and infrastructure teams, and it makes the approval process visible instead of scattered across chat, email, and ad hoc manual work.", size=20, spacing_after=40))
    for txt in [
        "Faster request submission: users describe what they want instead of filling rigid forms.",
        "Better governance: risky or destructive actions go through an explicit approval process.",
        "Auditability: every request, decision, and execution outcome is recorded.",
        "Reduced operational error: the assistant validates intent, tool choice, and execution path before acting.",
        "Transparency: users and admins can see pending, approved, rejected, and failed items in one system.",
        "Self-service at scale: common Azure operations can be initiated without opening a separate ticket for every request.",
        "Accessibility: voice input lowers friction for users who prefer speaking over typing.",
        "Actionable insight: the approval history and failure logs make it easier to understand recurring issues and process bottlenecks.",
    ]:
        parts.append(bullet(txt))

    parts.append(p("12. Practical Configuration Notes", style="Heading1", bold=True, size=28, color="1F4E78", spacing_before=120, spacing_after=40))
    parts.append(p("The system is driven by environment variables rather than hard-coded secrets. The most important runtime values are summarized below.", size=20, spacing_after=40))
    parts.append(table(
        ["Category", "Examples"],
        [
            ["Backend identity", "ENTRA_TENANT_ID, ENTRA_CLIENT_ID"],
            ["Azure execution", "AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_SUBSCRIPTION_ID"],
            ["Admin access", "ADMIN_USER_EMAILS"],
            ["Speech-to-text", "AZURE_SPEECH_KEY, AZURE_SPEECH_REGION, AZURE_SPEECH_LANGUAGE"],
            ["Local dev behavior", "DEV_BYPASS_AUTH"],
            ["Frontend auth", "VITE_ENTRA_CLIENT_ID, VITE_ENTRA_TENANT_ID, VITE_ENTRA_API_SCOPE, VITE_ENTRA_REDIRECT_URI"],
        ],
        widths=[2400, 8400]
    ))

    parts.append(p("13. PostgreSQL Schema, Relationships, and Sample Records", style="Heading1", bold=True, size=28, color="1F4E78", spacing_before=120, spacing_after=40))
    parts.append(p("The database is the system of record for identity, chat, summaries, approvals, execution outcomes, and auditability. The current model set is intentionally normalized so that user identity, chat state, approval state, and action history can be queried independently while still being linked by foreign keys.", size=20, spacing_after=40))
    parts.append(table(
        ["Table", "Core columns", "Purpose"],
        [
            ["users", "id, entra_oid, email, display_name, created_at", "Stores the signed-in Entra identity mapped to the application user."],
            ["chat_sessions", "id, user_id, status, created_at", "One row per conversational session; belongs to a user."],
            ["chat_messages", "id, session_id, role, content, created_at", "Stores each chat turn in a session."],
            ["session_memory", "id, user_id, session_id, source_session_id, summary, created_at", "Carries forward a compact summary from the prior session into the new one."],
            ["approval_requests", "id, user_id, session_id, action, payload, tool_name, status, approved, approved_by, decision_reason, approved_at, executed_at, result, error_message", "Tracks each change request, its status, the admin decision, and the execution outcome."],
            ["approval_action_logs", "id, approval_id, admin_email, action, status, reason, result_text, error_message, created_at", "Stores every approve/reject action as an auditable event."],
            ["audit_logs", "id, user_id, action, result, created_at", "Captures general audit events outside the approval workflow."],
        ],
        widths=[1800, 3900, 3600]
    ))
    parts.append(p("Relationship map", style="Heading2", bold=True, size=22, color="1F4E78", spacing_before=40, spacing_after=20))
    for rel in [
        "users 1 -> many chat_sessions: one user can open multiple chat conversations.",
        "chat_sessions 1 -> many chat_messages: each conversation stores many turns.",
        "users 1 -> many approval_requests: the user who asked for the change owns the request.",
        "chat_sessions 1 -> many approval_requests: each request is tied to the conversation that created it.",
        "users 1 -> many session_memory rows: one user can have a compact summary per session.",
        "chat_sessions 1 -> 1 session_memory: the session_id is unique in session_memory, so each new session stores at most one carry-forward summary.",
        "approval_requests 1 -> many approval_action_logs: one approval can have one or more action events over time.",
        "users 1 -> many audit_logs: audit entries are anchored to a user identity.",
    ]:
        parts.append(bullet(rel))
    parts.append(p("Sample records and what they mean", style="Heading2", bold=True, size=22, color="1F4E78", spacing_before=40, spacing_after=20))
    parts.append(table(
        ["Table", "Sample record", "Explanation"],
        [
            ["users", "id=2, email=admin_anirban@..., display_name=Admin Anirban", "This is the admin identity that can see all approvals and perform approve/reject actions."],
            ["chat_sessions", "id=49, user_id=2, status=ACTIVE", "A live session created after login; the user can continue the conversation in this thread."],
            ["chat_messages", "session_id=49, role=user, content='create a resource group...'", "One message in the chat history for the active session."],
            ["session_memory", "session_id=49, source_session_id=48, summary='User discussed resource groups, eastus, and approval steps'", "A compact summary of the previous session carried into the new one."],
            ["approval_requests", "id=15, session_id=49, user_id=2, status=PENDING, action='create_or_update_resource_group'", "A pending change request created by the chat flow; it waits for admin review."],
            ["approval_action_logs", "approval_id=15, admin_email=admin_anirban@..., action=APPROVE, status=FAILED, error_message='Invalid storage SKU ...'", "A recorded admin decision and the backend execution result."],
            ["audit_logs", "user_id=2, action='login', result='success'", "A general audit event outside the approval workflow."],
        ],
        widths=[1800, 4200, 3300]
    ))
    parts.append(p("The practical value of this structure is that the UI can show live chat history, the user can inspect their own requests, the admin can review a full approval trail, and support teams can trace execution outcomes without joining multiple unrelated tables manually.", size=20, spacing_after=60))

    parts.append(p("14. Closing Note", style="Heading1", bold=True, size=28, color="1F4E78", spacing_before=120, spacing_after=40))
    parts.append(p("The value of this project is not only in executing Azure operations, but in creating a repeatable, auditable, and business-friendly control plane for cloud work. The combination of chat, approvals, execution history, voice input, and role-based views turns a set of cloud APIs into an operational interface that business users can understand and trust.", size=20, spacing_after=60))
    parts.append(p("End of guide", align="center", italic=True, size=18, color="666666"))
    return "".join(parts)


def build_styles() -> str:
    return dedent(f"""
    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <w:styles xmlns:w="{W_NS}">
      <w:docDefaults>
        <w:rPrDefault>
          <w:rPr>
            <w:rFonts w:ascii="Aptos" w:hAnsi="Aptos"/>
            <w:sz w:val="22"/>
            <w:szCs w:val="22"/>
          </w:rPr>
        </w:rPrDefault>
      </w:docDefaults>
      <w:style w:type="paragraph" w:default="1" w:styleId="Normal">
        <w:name w:val="Normal"/>
        <w:qFormat/>
      </w:style>
      <w:style w:type="paragraph" w:styleId="Heading1">
        <w:name w:val="heading 1"/>
        <w:basedOn w:val="Normal"/><w:next w:val="Normal"/>
        <w:rPr><w:b/><w:color w:val="1F4E78"/><w:sz w:val="28"/><w:szCs w:val="28"/></w:rPr>
      </w:style>
      <w:style w:type="paragraph" w:styleId="Heading2">
        <w:name w:val="heading 2"/>
        <w:basedOn w:val="Normal"/><w:next w:val="Normal"/>
        <w:rPr><w:b/><w:color w:val="1F4E78"/><w:sz w:val="24"/><w:szCs w:val="24"/></w:rPr>
      </w:style>
      <w:style w:type="paragraph" w:styleId="Heading3">
        <w:name w:val="heading 3"/>
        <w:basedOn w:val="Normal"/><w:next w:val="Normal"/>
        <w:rPr><w:b/><w:color w:val="1F4E78"/><w:sz w:val="22"/><w:szCs w:val="22"/></w:rPr>
      </w:style>
      <w:style w:type="table" w:styleId="TableGrid">
        <w:name w:val="Table Grid"/>
        <w:tblPr><w:tblBorders>
          <w:top w:val="single" w:sz="4" w:space="0" w:color="BFBFBF"/>
          <w:left w:val="single" w:sz="4" w:space="0" w:color="BFBFBF"/>
          <w:bottom w:val="single" w:sz="4" w:space="0" w:color="BFBFBF"/>
          <w:right w:val="single" w:sz="4" w:space="0" w:color="BFBFBF"/>
          <w:insideH w:val="single" w:sz="4" w:space="0" w:color="D9D9D9"/>
          <w:insideV w:val="single" w:sz="4" w:space="0" w:color="D9D9D9"/>
        </w:tblBorders></w:tblPr>
      </w:style>
    </w:styles>
    """).strip()


def build_numbering() -> str:
    return dedent(f"""
    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <w:numbering xmlns:w="{W_NS}">
      <w:abstractNum w:abstractNumId="0">
        <w:multiLevelType w:val="hybridMultilevel"/>
        <w:lvl w:ilvl="0">
          <w:start w:val="1"/>
          <w:numFmt w:val="bullet"/>
          <w:lvlText w:val="•"/>
          <w:lvlJc w:val="left"/>
          <w:pPr><w:ind w:left="720" w:hanging="360"/></w:pPr>
        </w:lvl>
      </w:abstractNum>
      <w:abstractNum w:abstractNumId="1">
        <w:multiLevelType w:val="hybridMultilevel"/>
        <w:lvl w:ilvl="0">
          <w:start w:val="1"/>
          <w:numFmt w:val="decimal"/>
          <w:lvlText w:val="%1."/>
          <w:lvlJc w:val="left"/>
          <w:pPr><w:ind w:left="720" w:hanging="360"/></w:pPr>
        </w:lvl>
      </w:abstractNum>
      <w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num>
      <w:num w:numId="2"><w:abstractNumId w:val="1"/></w:num>
    </w:numbering>
    """).strip()


def build_content_types() -> str:
    return dedent(f"""
    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <Types xmlns="{CT_NS}">
      <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
      <Default Extension="xml" ContentType="application/xml"/>
      <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
      <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
      <Override PartName="/word/numbering.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml"/>
      <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
      <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
    </Types>
    """).strip()


def build_root_rels() -> str:
    return dedent(f"""
    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <Relationships xmlns="{P_NS}">
      <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
      <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
      <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
    </Relationships>
    """).strip()


def build_document_rels() -> str:
    return dedent(f"""
    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <Relationships xmlns="{P_NS}">
      <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
      <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/numbering" Target="numbering.xml"/>
    </Relationships>
    """).strip()


def build_core_props() -> str:
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return dedent(f"""
    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <cp:coreProperties xmlns:cp="{CP_NS}" xmlns:dc="{DC_NS}" xmlns:dcterms="{DCT_NS}" xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
      <dc:title>Azure AI Ops Platform Architecture Guide</dc:title>
      <dc:subject>Architecture, design flow, business value</dc:subject>
      <dc:creator>OpenAI Codex</dc:creator>
      <cp:lastModifiedBy>OpenAI Codex</cp:lastModifiedBy>
      <dcterms:created xsi:type="dcterms:W3CDTF">{now}</dcterms:created>
      <dcterms:modified xsi:type="dcterms:W3CDTF">{now}</dcterms:modified>
    </cp:coreProperties>
    """).strip()


def build_app_props() -> str:
    return dedent("""
    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
      <Application>Microsoft Office Word</Application>
      <DocSecurity>0</DocSecurity>
      <ScaleCrop>false</ScaleCrop>
      <HeadingPairs>
        <vt:vector size="2" baseType="variant">
          <vt:variant><vt:lpstr>Title</vt:lpstr></vt:variant>
          <vt:variant><vt:i4>1</vt:i4></vt:variant>
        </vt:vector>
      </HeadingPairs>
      <TitlesOfParts>
        <vt:vector size="1" baseType="lpstr">
          <vt:lpstr>Azure AI Ops Platform Architecture and Business Guide</vt:lpstr>
        </vt:vector>
      </TitlesOfParts>
      <Company></Company>
      <LinksUpToDate>false</LinksUpToDate>
      <SharedDoc>false</SharedDoc>
      <HyperlinksChanged>false</HyperlinksChanged>
      <AppVersion>16.0000</AppVersion>
    </Properties>
    """).strip()


def build_document_xml() -> str:
    body = build_document_body()
    return dedent(f"""
    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <w:document xmlns:w="{W_NS}" xmlns:r="{R_NS}">
      <w:body>
        {body}
        <w:sectPr>
          <w:pgSz w:w="12240" w:h="15840"/>
          <w:pgMar w:top="1080" w:right="1152" w:bottom="1080" w:left="1152" w:header="708" w:footer="708" w:gutter="0"/>
        </w:sectPr>
      </w:body>
    </w:document>
    """).strip()


def build_docx(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(path, "w", ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", build_content_types())
        z.writestr("_rels/.rels", build_root_rels())
        z.writestr("docProps/core.xml", build_core_props())
        z.writestr("docProps/app.xml", build_app_props())
        z.writestr("word/document.xml", build_document_xml())
        z.writestr("word/styles.xml", build_styles())
        z.writestr("word/numbering.xml", build_numbering())
        z.writestr("word/_rels/document.xml.rels", build_document_rels())


if __name__ == "__main__":
    build_docx(OUT)
    print(OUT)
