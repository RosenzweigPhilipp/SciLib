from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from .config import settings
import time
import logging

logger = logging.getLogger(__name__)
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
    token = credentials.credentials
    logger.debug(f"Verifying token: {token[:8]}..." if len(token) > 8 else token)

    # Check if it's the master API key (for backward compatibility)
    if token == settings.api_key:
        logger.debug("Token matches master API key")
        return token

    # For other session tokens, import active_sessions lazily to avoid circular import
    try:
        from .main import active_sessions  # Import here to avoid circular import
    except Exception:
        logger.warning("Could not import active_sessions; rejecting non-master tokens")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session token. Please login again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check session token
    if token not in active_sessions:
        logger.warning(f"Token not found in active sessions. Active sessions: {len(active_sessions)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session token. Please login again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    session = active_sessions[token]
    if time.time() > session["expires_at"]:
        logger.warning(f"Token expired. Current time: {time.time()}, expires at: {session['expires_at']}")
        # Clean up expired session
        del active_sessions[token]
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired. Please login again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.debug("Token verification successful")
    return token