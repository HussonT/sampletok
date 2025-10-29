"""
Rate limiting configuration using SlowAPI.

For development: Uses in-memory storage
For production: Configure with Redis for distributed rate limiting
"""

from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request
from typing import Callable


def get_user_id_or_ip(request: Request) -> str:
    """
    Get rate limit key from user ID (if authenticated) or IP address (if not).
    This ensures authenticated users are rate-limited per user, not per IP.
    """
    # Try to get user from request state (set by auth middleware)
    if hasattr(request.state, "user") and request.state.user:
        return f"user:{request.state.user.id}"

    # Fall back to IP address for unauthenticated requests
    return f"ip:{get_remote_address(request)}"


# Initialize the limiter
# In production, you can configure this to use Redis:
# storage_uri = "redis://localhost:6379"
# limiter = Limiter(key_func=get_user_id_or_ip, storage_uri=storage_uri)
limiter = Limiter(key_func=get_user_id_or_ip)


def create_rate_limit_key_func(user_required: bool = True) -> Callable:
    """
    Create a custom rate limit key function.

    Args:
        user_required: If True, rate limit by user ID only (requires authentication).
                      If False, rate limit by user ID or IP address.

    Returns:
        A function that extracts the rate limit key from the request.
    """
    if user_required:
        def user_key_func(request: Request) -> str:
            if hasattr(request.state, "user") and request.state.user:
                return f"user:{request.state.user.id}"
            # This should never happen if authentication is enforced
            return f"anonymous:{get_remote_address(request)}"
        return user_key_func
    else:
        return get_user_id_or_ip
