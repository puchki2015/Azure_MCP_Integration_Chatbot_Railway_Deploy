from jose import jwt
import httpx

from app.config.settings import get_settings

settings = get_settings()


class JWTValidator:

    def __init__(self):

        self.jwks_url = (
            f"https://login.microsoftonline.com/"
            f"{settings.ENTRA_TENANT_ID}"
            f"/discovery/v2.0/keys"
        )
        self.issuer = (
            f"https://login.microsoftonline.com/"
            f"{settings.ENTRA_TENANT_ID}"
            f"/v2.0"
        )
        self.legacy_issuer = (
            f"https://sts.windows.net/"
            f"{settings.ENTRA_TENANT_ID}"
            f"/"
        )
        self._jwks = None

    async def get_signing_keys(self):

        if self._jwks:
            return self._jwks

        async with httpx.AsyncClient() as client:

            response = await client.get(
                self.jwks_url,
                timeout=10
            )

            response.raise_for_status()

            self._jwks = response.json()

            return self._jwks

    async def validate_token(
        self,
        token: str
    ):

        jwks = await self.get_signing_keys()

        unverified_header = jwt.get_unverified_header(
            token
        )

        rsa_key = {}

        for key in jwks["keys"]:

            if key["kid"] == unverified_header["kid"]:

                rsa_key = {
                    "kty": key["kty"],
                    "kid": key["kid"],
                    "use": key["use"],
                    "n": key["n"],
                    "e": key["e"],
                }

        if not rsa_key:
            raise ValueError(
                "Unable to find a matching signing key"
            )

        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            issuer=[self.issuer, self.legacy_issuer],
            options={"verify_aud": False}
        )

        audience = payload.get("aud")
        accepted_audiences = {
            settings.ENTRA_CLIENT_ID,
            f"api://{settings.ENTRA_CLIENT_ID}"
        }

        if audience not in accepted_audiences:
            raise ValueError(
                f"Invalid token audience: {audience}"
            )

        return payload
