"""Shared dependencies: authentication, etc."""
from fastapi import Header, HTTPException


async def verify_token(authorization: str = Header(..., description="Bearer {token}")):
    """Verify the Authorization header (placeholder implementation)."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid Authorization header format. Expected: Bearer {token}")
    token = authorization[len("Bearer "):]
    if not token:
        raise HTTPException(status_code=401, detail="Token is missing")
    # TODO: Implement real token validation logic
    return token
