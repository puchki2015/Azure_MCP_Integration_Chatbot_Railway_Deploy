# app/agents/approval_guard.py

DESTRUCTIVE_KEYWORDS = {

    "create",

    "delete",

    "update",

    "modify",

    "restart",

    "deploy",

    "destroy",

    "remove",

    "shutdown",

    "start vm",

    "stop vm",

    "resize vm"
}


def requires_approval(
    user_message: str
) -> bool:

    msg = user_message.lower()

    return any(
        keyword in msg
        for keyword in DESTRUCTIVE_KEYWORDS
    )