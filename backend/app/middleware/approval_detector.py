MUTATING_KEYWORDS = [
    "create",
    "delete",
    "update",
    "restart",
    "stop",
    "start",
    "scale",
    "assign",
    "grant"
]


def requires_approval(message: str):

    text = message.lower()

    return any(
        keyword in text
        for keyword in MUTATING_KEYWORDS
    )