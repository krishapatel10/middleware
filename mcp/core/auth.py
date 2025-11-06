# core/auth.py
import logging
from typing import Optional
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = logging.getLogger(__name__)
bearer = HTTPBearer(auto_error=False)

async def verify_jwt(credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer)) -> dict:
    if not credentials or not credentials.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Authorization")
    token = credentials.credentials
    # Replace with real verification, e.g. PyJWT decode, introspection, etc.
    try:
        # payload = jwt.decode(token, key=..., algorithms=["RS256"])
        payload = {"sub": "expertiza", "role": "system"}  # placeholder
        return payload
    except Exception as exc:
        logger.exception("Invalid token")
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
