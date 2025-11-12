
from typing import Optional
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt, JWTError
from dotenv import load_dotenv
import os

bearer = HTTPBearer(auto_error=False)

load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
# async def verify_jwt(credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer)) -> dict:
#     if not credentials or not credentials.credentials:
#         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Authorization")
#     token = credentials.credentials

#     try:
#         payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
#         return payload
#     except JWTError:
#         raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

# from typing import Optional
# from fastapi import Depends, HTTPException, status
# from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# bearer = HTTPBearer(auto_error=False)

# Dummy verification for development and SSO placeholder
async def verify_jwt(credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer)) -> dict:
    """
    Temporary JWT/SSO verification stub.
    In production, this should verify the university's SSO-issued token or headers.
    """
    # No Authorization header
    if not credentials or not credentials.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Authorization")

    token = credentials.credentials

    # --- Dummy acceptance for local testing ---
    # Accept any non-empty token and simulate an SSO payload
    if token == "dev" or token.startswith("dummy"):
        return {"sub": "local_dev_user", "role": "tester"}

    # In production, replace this with real validation (SSO or JWT)
    # e.g., decode and verify SSO token, or call university's introspection endpoint
    raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
