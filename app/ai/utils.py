"""
Utility functions for AI operations including retry logic.
"""
import time
import logging
from functools import wraps
from typing import Callable, Any, Optional

logger = logging.getLogger(__name__)


def retry_with_exponential_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    exponential_base: float = 2.0,
    max_delay: float = 60.0,
    exceptions: tuple = (Exception,)
) -> Callable:
    """
    Decorator that retries a function with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds before first retry
        exponential_base: Base for exponential backoff calculation
        max_delay: Maximum delay between retries in seconds
        exceptions: Tuple of exception types to catch and retry
    
    Returns:
        Decorated function with retry logic
    
    Example:
        @retry_with_exponential_backoff(max_retries=3, initial_delay=1.0)
        def call_external_api():
            response = requests.get("https://api.example.com")
            return response.json()
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            delay = initial_delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_retries:
                        logger.error(
                            f"{func.__name__} failed after {max_retries} retries. "
                            f"Last error: {str(e)}"
                        )
                        raise
                    
                    # Calculate next delay with exponential backoff
                    wait_time = min(delay, max_delay)
                    logger.warning(
                        f"{func.__name__} attempt {attempt + 1} failed: {str(e)}. "
                        f"Retrying in {wait_time:.1f}s..."
                    )
                    
                    time.sleep(wait_time)
                    delay *= exponential_base
            
            # Should not reach here, but just in case
            raise last_exception
        
        return wrapper
    return decorator


def async_retry_with_exponential_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    exponential_base: float = 2.0,
    max_delay: float = 60.0,
    exceptions: tuple = (Exception,)
) -> Callable:
    """
    Async version of retry decorator with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds before first retry
        exponential_base: Base for exponential backoff calculation
        max_delay: Maximum delay between retries in seconds
        exceptions: Tuple of exception types to catch and retry
    
    Returns:
        Decorated async function with retry logic
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            import asyncio
            
            delay = initial_delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_retries:
                        logger.error(
                            f"{func.__name__} failed after {max_retries} retries. "
                            f"Last error: {str(e)}"
                        )
                        raise
                    
                    # Calculate next delay with exponential backoff
                    wait_time = min(delay, max_delay)
                    logger.warning(
                        f"{func.__name__} attempt {attempt + 1} failed: {str(e)}. "
                        f"Retrying in {wait_time:.1f}s..."
                    )
                    
                    await asyncio.sleep(wait_time)
                    delay *= exponential_base
            
            # Should not reach here, but just in case
            raise last_exception
        
        return wrapper
    return decorator
