from pydantic import BaseModel


class UserInfo(BaseModel):

    oid: str

    email: str

    display_name: str

    is_admin: bool = False
