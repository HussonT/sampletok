"""
FastAPI dependencies for authentication and database access.

Authentication Strategy:
- Uses ONLY Clerk user ID (sub claim) from JWT
- Email and username are optional metadata - not required for authentication
- New users are created automatically with Clerk ID as primary identifier
"""
from typing import Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.clerk_auth import get_current_user_from_clerk, get_optional_user_from_clerk
from app.services.user_service import get_or_create_user_from_clerk, get_user_by_clerk_id
from app.models.user import User


async def get_current_user(
    clerk_claims: dict = Depends(get_current_user_from_clerk),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Get the current authenticated user from the database.
    Creates the user if this is their first login.
    Uses ONLY Clerk ID - email not required.

    Args:
        clerk_claims: JWT claims from Clerk token
        db: Database session

    Returns:
        User object from database

    Raises:
        HTTPException: If user cannot be loaded/created
    """
    # Extract Clerk user ID from JWT
    clerk_user_id = clerk_claims.get("sub")

    if not clerk_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing user ID"
        )

    # Try to find existing user by Clerk ID
    existing_user = await get_user_by_clerk_id(db, clerk_user_id)
    if existing_user:
        return existing_user

    # User doesn't exist - create new user with Clerk ID only
    # Email and username are optional metadata
    try:
        user = await get_or_create_user_from_clerk(
            db=db,
            clerk_user_id=clerk_user_id,
            email=clerk_claims.get("email"),  # Optional
            username=clerk_claims.get("username")  # Optional
        )
        return user
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load user: {str(e)}"
        )


async def get_current_user_optional(
    clerk_claims: Optional[dict] = Depends(get_optional_user_from_clerk),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    Optionally get the current authenticated user from the database.
    Returns None if no valid authentication is present.
    Uses ONLY Clerk ID - email not required.

    Args:
        clerk_claims: JWT claims from Clerk token (or None)
        db: Database session

    Returns:
        User object from database, or None if not authenticated
    """
    if not clerk_claims:
        return None

    # Extract Clerk user ID from JWT
    clerk_user_id = clerk_claims.get("sub")

    if not clerk_user_id:
        return None

    try:
        # Try to find existing user by Clerk ID
        existing_user = await get_user_by_clerk_id(db, clerk_user_id)
        if existing_user:
            return existing_user

        # User doesn't exist - create new user with Clerk ID only
        user = await get_or_create_user_from_clerk(
            db=db,
            clerk_user_id=clerk_user_id,
            email=clerk_claims.get("email"),  # Optional
            username=clerk_claims.get("username")  # Optional
        )
        return user
    except Exception:
        return None
