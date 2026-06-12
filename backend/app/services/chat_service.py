from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from openai import AsyncOpenAI

from app.middleware.approval_detector import requires_approval
from app.services.approval_service import approval_service



from app.database.models import (
    ChatSession,
    ChatMessage,
    AuditLog,
    SessionMemory
)

from app.agents.azure_agent import (
    azure_agent
)


class ChatService:

    def __init__(self):
        self.client = AsyncOpenAI()
        self.settings = None
        try:
            from app.config.settings import get_settings
            self.settings = get_settings()
        except Exception:
            self.settings = None

    def _extract_session_summary(
        self,
        messages: list[dict]
    ) -> str:
        if not messages:
            return "No prior conversation context was available."

        joined = "\n".join(
            f"{message['role']}: {message['content']}"
            for message in messages
            if message.get("content")
        )

        if not joined.strip():
            return "No prior conversation context was available."

        import re

        rg_match = re.findall(
            r"(?:resource group(?: called| named| with name)?\s+)([a-zA-Z0-9._-]+)",
            joined,
            flags=re.IGNORECASE
        )
        region_match = re.findall(
            r"\b(east\s+us|west\s+us|central\s+us|north\s+central\s+us|south\s+central\s+us|eastus|westus|centralus|northeurope|westeurope)\b",
            joined,
            flags=re.IGNORECASE
        )
        approval_match = re.findall(
            r"approval id[:\s]+(\d+)",
            joined,
            flags=re.IGNORECASE
        )

        topics: list[str] = []

        if rg_match:
            topics.append(
                f"resource group(s): {', '.join(dict.fromkeys(rg_match[-3:]))}"
            )

        if region_match:
            normalized_regions = [
                region.replace("  ", " ").strip().lower()
                for region in region_match[-3:]
            ]
            topics.append(
                f"region(s): {', '.join(dict.fromkeys(normalized_regions))}"
            )

        if approval_match:
            topics.append(
                f"approval id(s): {', '.join(dict.fromkeys(approval_match[-3:]))}"
            )

        if not topics:
            recent_lines = [
                f"{message['role']}: {str(message['content']).strip()[:180]}"
                for message in messages[-6:]
                if message.get("content")
            ]
            topics.append("; ".join(recent_lines))

        return "Previous session context: " + " | ".join(topics)

    def _format_summary_fallback(self, messages: list[dict]) -> str:
        if not messages:
            return "No prior conversation context was available."

        notable_points: list[str] = []
        for message in messages:
            role = str(message.get("role", "")).lower()
            content = str(message.get("content", "")).strip()
            if not content:
                continue

            if role == "user":
                notable_points.append(f"User asked: {content[:220]}")
            elif role == "assistant":
                notable_points.append(f"Assistant replied: {content[:220]}")

        if not notable_points:
            notable_points = [
                f"{str(message.get('role', 'unknown')).lower()}: {str(message.get('content', '')).strip()[:220]}"
                for message in messages[-6:]
                if message.get("content")
            ]

        return " | ".join(notable_points[:8])[:1200]

    async def _generate_session_summary(
        self,
        messages: list[dict]
    ) -> str:
        transcript = "\n".join(
            f"{str(message.get('role', 'unknown')).upper()}: {str(message.get('content', '')).strip()}"
            for message in messages
            if message.get("content")
        )

        if not transcript.strip():
            return "No prior conversation context was available."

        prompt = (
            "Summarize the following Azure AI Ops conversation for use in the "
            "next session. Write 3 to 6 concise sentences. Include: user intent, "
            "important Azure resources or names, regions, approvals mentioned, "
            "resolved or unresolved follow-ups, and anything the next session should remember. "
            "Do not use bullet points. Do not mention that you are summarizing.\n\n"
            f"Conversation:\n{transcript}"
        )

        if not self.settings:
            return self._format_summary_fallback(messages)

        try:
            response = await self.client.chat.completions.create(
                model=self.settings.OPENAI_SUMMARY_MODEL,
                temperature=0,
                messages=[
                    {
                        "role": "system",
                        "content": "You produce compact, accurate session summaries."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            summary = response.choices[0].message.content or ""
            summary = summary.strip()
            if summary:
                return summary
        except Exception as ex:
            print(f"Session summary generation failed: {ex}")

        return self._format_summary_fallback(messages)

    async def _get_last_session_memory(
        self,
        db: Session,
        user_id: int,
        current_session_id: int
    ) -> SessionMemory | None:
        return (
            db.query(SessionMemory)
            .filter(
                SessionMemory.user_id == user_id,
                SessionMemory.session_id != current_session_id
            )
            .order_by(SessionMemory.created_at.desc())
            .first()
        )

    async def _save_session_memory(
        self,
        db: Session,
        user_id: int,
        session_id: int,
        source_session_id: int | None,
        summary: str
    ) -> SessionMemory:
        memory = SessionMemory(
            user_id=user_id,
            session_id=session_id,
            source_session_id=source_session_id,
            summary=summary
        )
        db.add(memory)
        db.commit()
        db.refresh(memory)
        return memory

    async def get_recent_history(
        self,
        db: Session,
        session_id: int,
        user_id: int,
        limit: int = 8
    ) -> list[dict]:

        messages = (
            db.query(ChatMessage)
            .join(ChatSession)
            .filter(
                ChatMessage.session_id == session_id,
                ChatSession.user_id == user_id
            )
            .order_by(
                ChatMessage.created_at.desc()
            )
            .limit(limit)
            .all()
        )

        return [
            {
                "role": message.role,
                "content": message.content,
                "created_at": message.created_at
            }
            for message in reversed(messages)
        ]

    async def create_session(
        self,
        db: Session,
        user_id: int | None = None
    ) -> ChatSession:

        try:

            session = ChatSession(
                user_id=user_id
            )

            db.add(session)
            db.commit()
            db.refresh(session)

            if user_id is not None:
                previous_session = (
                    db.query(ChatSession)
                    .filter(
                        ChatSession.user_id == user_id,
                        ChatSession.id != session.id
                    )
                    .order_by(ChatSession.created_at.desc(), ChatSession.id.desc())
                    .first()
                )

                if previous_session:
                    previous_messages = await self.get_recent_history(
                        db=db,
                        session_id=previous_session.id,
                        user_id=user_id,
                        limit=30
                    )
                    summary = await self._generate_session_summary(
                        previous_messages
                    )
                    await self._save_session_memory(
                        db=db,
                        user_id=user_id,
                        session_id=session.id,
                        source_session_id=previous_session.id,
                        summary=summary
                    )

            print(
                f"Created chat session: {session.id}"
            )

            return session

        except SQLAlchemyError as ex:

            db.rollback()

            print(
                f"Failed creating session: {ex}"
            )

            raise

    async def get_session(
        self,
        db: Session,
        session_id: int,
        user_id: int | None = None
    ) -> ChatSession | None:

        query = (
            db.query(ChatSession)
            .filter(
                ChatSession.id == session_id
            )
        )

        if user_id is not None:
            query = query.filter(
                ChatSession.user_id == user_id
            )

        return query.first()

    async def save_message(
        self,
        db: Session,
        session_id: int,
        role: str,
        content: str
    ) -> ChatMessage:

        try:

            message = ChatMessage(
                session_id=session_id,
                role=role,
                content=content
            )

            db.add(message)
            db.commit()
            db.refresh(message)

            return message

        except SQLAlchemyError as ex:

            db.rollback()

            print(
                f"Failed saving message: {ex}"
            )

            raise

    async def write_audit_log(
        self,
        db: Session,
        user_id: int,
        action: str,
        result: str
    ):

        try:

            audit = AuditLog(
                user_id=user_id,
                action=action[:5000],
                result=result[:10000]
            )

            db.add(audit)
            db.commit()
            db.refresh(audit)

            print(
                f"Audit log written: {audit.id}"
            )

            return audit

        except SQLAlchemyError as ex:

            db.rollback()

            print(
                f"Audit log failed: {ex}"
            )

            return None

    async def send_message(
        self,
        db: Session,
        session_id: int,
        user_message: str,
        user_id: int,
        user_email: str | None = None
    ) -> dict:

        session = await self.get_session(
            db=db,
            session_id=session_id,
            user_id=user_id
        )

        if not session:

            raise Exception(
                f"Session {session_id} not found"
            )

        await self.save_message(
            db=db,
            session_id=session_id,
            role="user",
            content=user_message
        )

        recent_history = await self.get_recent_history(
            db=db,
            session_id=session_id,
            user_id=user_id
        )

        session_memory = (
            db.query(SessionMemory)
            .filter(
                SessionMemory.session_id == session_id,
                SessionMemory.user_id == user_id
            )
            .first()
        )

        if session_memory:
            recent_history = [
                {
                    "role": "system",
                    "content": session_memory.summary,
                    "created_at": session_memory.created_at
                }
            ] + recent_history

        resolution = None

        try:
            from app.services.tool_resolver import tool_resolver

            resolution = await tool_resolver.resolve(
                message=user_message,
                conversation_history=recent_history
            )
        except Exception as ex:
            if requires_approval(user_message):
                response = (
                    "I could not prepare a valid Azure change request. "
                    f"Please add the missing resource details. Error: {ex}"
                )

                await self.save_message(
                    db=db,
                    session_id=session_id,
                    role="assistant",
                    content=response
                )

                return {
                    "response": response,
                    "requires_approval": False,
                    "approval_id": None,
                    "approval_user_email": None
                }

            resolution = None

        if resolution and (
            resolution.requires_approval
            or requires_approval(user_message)
        ):
            approval = await approval_service.create_request(
                db=db,
                session_id=session_id,
                user_id=user_id,
                action=user_message,
                tool_name=resolution.tool_name,
                payload=resolution.payload
            )

            response = (
                f"Your message requires approval. "
                f"Approval ID: {approval.id}. "
                f"Requested by: {user_email or 'unknown user'}"
            )

            await self.save_message(
                db=db,
                session_id=session_id,
                role="assistant",
                content=response
            )

            return {
                "response": response,
                "requires_approval": True,
                "approval_id": approval.id,
                "approval_user_email": user_email or getattr(getattr(approval, "user", None), "email", None)
            }

        

        response = await azure_agent.invoke(
            user_message,
            str(session_id),
            memory_context=session_memory.summary if session_memory else None
        )

        await self.save_message(
            db=db,
            session_id=session_id,
            role="assistant",
            content=response
        )

        await self.write_audit_log(
            db=db,
            user_id=user_id,
            action=user_message,
            result=response
        )

        return {
            "response": response,
            "requires_approval": False,
            "approval_id": None,
            "approval_user_email": None
        }

    async def get_history(
        self,
        db: Session,
        session_id: int,
        user_id: int
    ):

        return (
            db.query(ChatMessage)
            .join(ChatSession)
            .filter(
                ChatMessage.session_id == session_id,
                ChatSession.user_id == user_id
            )
            .order_by(
                ChatMessage.created_at
            )
            .all()
        )

    async def get_session_summary(
        self,
        db: Session,
        session_id: int,
        user_id: int
    ) -> SessionMemory | None:
        return (
            db.query(SessionMemory)
            .filter(
                SessionMemory.session_id == session_id,
                SessionMemory.user_id == user_id
            )
            .first()
        )

    async def get_latest_session_summary(
        self,
        db: Session,
        user_id: int
    ) -> SessionMemory | None:
        return (
            db.query(SessionMemory)
            .filter(
                SessionMemory.user_id == user_id
            )
            .order_by(SessionMemory.created_at.desc())
            .first()
        )


chat_service = ChatService()
