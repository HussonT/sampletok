"""
Clerk authentication utilities for FastAPI backend.

This module provides functions to verify Clerk JWT tokens and extract user information.
"""

import jwt
import httpx
from typing import Optional, Dict, Any
from fastapi import HTTPException, status, Header
from functools import lru_cache

from app.core.config import settings


@lru_cache(maxsize=1)
def get_clerk_jwks() -> Dict[str, Any]:
    """
    Fetch and cache Clerk's JWKS (JSON Web Key Set) for token verification.

    Returns:
        Dict containing the JWKS data

    Raises:
        HTTPException: If JWKS cannot be fetched
    """
    try:
        response = httpx.get(
            f"https://{settings.CLERK_FRONTEND_API}/.well-known/jwks.json",
            timeout=10.0
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch Clerk JWKS: {str(e)}"
        )


def verify_clerk_token(token: str) -> Dict[str, Any]:
    """
    Verify a Clerk JWT token and extract the claims.

    Args:
        token: The JWT token to verify

    Returns:
        Dict containing the decoded token claims

    Raises:
        HTTPException: If token is invalid or verification fails
    """
    try:
        # Get the JWKS
        jwks = get_clerk_jwks()

        # Decode the token header to get the key ID (kid)
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")

        if not kid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing key ID"
            )

        # Find the matching key in JWKS
        key = None
        for jwk_key in jwks.get("keys", []):
            if jwk_key.get("kid") == kid:
                key = jwk_key
                break

        if not key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unable to find matching key in JWKS"
            )

        # Convert JWK to PEM format for verification
        public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key)

        # Verify and decode the token
        # Note: Clerk tokens don't require all standard claims
        decoded = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            options={
                "verify_exp": True,
                "verify_aud": False,  # Don't require audience claim
                "verify_iss": False,  # Don't require issuer claim
                "require": []  # Don't require any specific claims
            }
        )

        return decoded

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token verification failed: {str(e)}"
        )


async def get_current_user_from_clerk(
    authorization: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """
    FastAPI dependency to get the current user from Clerk JWT token.

    Args:
        authorization: The Authorization header containing the Bearer token

    Returns:
        Dict containing user information from the token

    Raises:
        HTTPException: If authorization is missing or invalid
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Extract the token from "Bearer <token>"
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format. Expected: Bearer <token>",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = parts[1]

    # Verify the token and extract claims
    claims = verify_clerk_token(token)

    return claims


async def get_optional_user_from_clerk(
    authorization: Optional[str] = Header(None)
) -> Optional[Dict[str, Any]]:
    """
    FastAPI dependency to optionally get the current user from Clerk JWT token.
    Returns None if no authorization header is present.

    Args:
        authorization: The Authorization header containing the Bearer token

    Returns:
        Dict containing user information from the token, or None if not authenticated
    """
    if not authorization:
        return None

    try:
        return await get_current_user_from_clerk(authorization)
    except HTTPException:
        return None
