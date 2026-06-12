from pydantic import BaseModel


class SpeechTokenResponse(BaseModel):
    token: str
    region: str
    language: str
    expires_in: int
