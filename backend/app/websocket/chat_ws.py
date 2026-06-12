from fastapi import APIRouter
from fastapi import WebSocket
from fastapi import WebSocketDisconnect

from app.agents.azure_agent import (
    azure_agent
)

router = APIRouter()


@router.websocket(
    "/chat/{session_id}"
)
async def websocket_chat(
    websocket: WebSocket,
    session_id: int
):

    await websocket.accept()

    try:

        while True:

            message = await websocket.receive_text()

            response = await azure_agent.invoke(
                message,
                str(session_id)
            )

            await websocket.send_text(
                response
            )

    except WebSocketDisconnect:

        print(
            f"Session disconnected: {session_id}"
        )
