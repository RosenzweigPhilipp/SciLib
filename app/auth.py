from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from .config import settings
import time

security = HTTPBearer()


def verify_api_key(credentials: HTTPAuthorizationCredentials = Security(security)):
    """
    Verify API key authentication
    """
    if credentials.credentials != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials


def verify_session_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    """
    Verify session token authentication
    """
    from .main import active_sessions  # Import here to avoid circular import
    
    token = credentials.credentials
    
    # Check if it's the master API key (for backward compatibility)
    if token == settings.api_key:
        return token
    
    # Check session token
    if token not in active_sessions:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    session = active_sessions[token]
    if time.time() > session["expires_at"]:
        # Clean up expired session
        del active_sessions[token]
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return token