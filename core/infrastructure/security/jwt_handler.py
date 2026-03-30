"""JWT token authentication and management."""

import logging
import jwt
import secrets
from datetime import datetime, timedelta
from typing import Dict, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TokenPayload:
    """JWT token payload."""

    user_id: str
    username: str
    email: str
    roles: list
    permissions: list
    iat: int  # Issued at
    exp: int  # Expiration
    jti: str  # JWT ID (unique identifier)


class JWTTokenHandler:
    """JWT token generation and validation."""

    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        """Initialize token handler."""
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire_minutes = 60
        self.refresh_token_expire_days = 7
        self.issued_tokens: Dict[str, Dict] = {}  # Token registry for revocation

    def generate_access_token(
        self,
        user_id: str,
        username: str,
        email: str,
        roles: list,
        permissions: list,
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """Generate access token."""
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=self.access_token_expire_minutes
            )

        jti = secrets.token_urlsafe(32)
        iat = int(datetime.utcnow().timestamp())
        exp = int(expire.timestamp())

        payload = {
            "user_id": user_id,
            "username": username,
            "email": email,
            "roles": roles,
            "permissions": permissions,
            "type": "access",
            "iat": iat,
            "exp": exp,
            "jti": jti,
        }

        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

        # Register token
        self.issued_tokens[jti] = {
            "type": "access",
            "user_id": user_id,
            "issued_at": datetime.utcnow(),
            "expires_at": expire,
            "revoked": False,
        }

        logger.debug(f"Generated access token for user {user_id}")
        return token

    def generate_refresh_token(self, user_id: str) -> str:
        """Generate refresh token."""
        expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)
        jti = secrets.token_urlsafe(32)
        iat = int(datetime.utcnow().timestamp())
        exp = int(expire.timestamp())

        payload = {
            "user_id": user_id,
            "type": "refresh",
            "iat": iat,
            "exp": exp,
            "jti": jti,
        }

        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

        # Register token
        self.issued_tokens[jti] = {
            "type": "refresh",
            "user_id": user_id,
            "issued_at": datetime.utcnow(),
            "expires_at": expire,
            "revoked": False,
        }

        logger.debug(f"Generated refresh token for user {user_id}")
        return token

    def verify_token(self, token: str) -> Optional[Dict]:
        """Verify and decode token."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])

            # Check if token is revoked
            jti = payload.get("jti")
            if jti in self.issued_tokens:
                token_info = self.issued_tokens[jti]
                if token_info.get("revoked"):
                    logger.warning(f"Token {jti} is revoked")
                    return None

            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Token is expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None

    def decode_token(self, token: str) -> Optional[TokenPayload]:
        """Decode token to payload."""
        payload = self.verify_token(token)
        if not payload:
            return None

        try:
            return TokenPayload(
                user_id=payload.get("user_id"),
                username=payload.get("username"),
                email=payload.get("email"),
                roles=payload.get("roles", []),
                permissions=payload.get("permissions", []),
                iat=payload.get("iat"),
                exp=payload.get("exp"),
                jti=payload.get("jti"),
            )
        except Exception as e:
            logger.error(f"Error decoding token: {e}")
            return None

    def revoke_token(self, token: str) -> bool:
        """Revoke token (add to blacklist)."""
        payload = self.verify_token(token)
        if not payload:
            return False

        jti = payload.get("jti")
        if jti in self.issued_tokens:
            self.issued_tokens[jti]["revoked"] = True
            logger.info(f"Revoked token {jti}")
            return True

        return False

    def revoke_user_tokens(self, user_id: str) -> int:
        """Revoke all tokens for user."""
        count = 0
        for jti, token_info in self.issued_tokens.items():
            if token_info.get("user_id") == user_id and not token_info.get("revoked"):
                token_info["revoked"] = True
                count += 1

        logger.info(f"Revoked {count} tokens for user {user_id}")
        return count

    def cleanup_expired_tokens(self) -> int:
        """Remove expired token entries from registry."""
        now = datetime.utcnow()
        expired_jtis = [
            jti
            for jti, info in self.issued_tokens.items()
            if info.get("expires_at", now) < now
        ]

        for jti in expired_jtis:
            del self.issued_tokens[jti]

        logger.debug(f"Cleaned up {len(expired_jtis)} expired token entries")
        return len(expired_jtis)

    def get_token_info(self, token: str) -> Optional[Dict]:
        """Get token information."""
        payload = self.verify_token(token)
        if not payload:
            return None

        jti = payload.get("jti")
        if jti not in self.issued_tokens:
            return None

        token_info = self.issued_tokens[jti]
        return {
            "user_id": payload.get("user_id"),
            "type": token_info.get("type"),
            "issued_at": token_info.get("issued_at"),
            "expires_at": token_info.get("expires_at"),
            "revoked": token_info.get("revoked"),
            "jti": jti,
        }

    def is_token_valid(self, token: str) -> bool:
        """Check if token is valid."""
        return self.verify_token(token) is not None

    def get_statistics(self) -> Dict:
        """Get token statistics."""
        now = datetime.utcnow()
        active_tokens = sum(
            1
            for t in self.issued_tokens.values()
            if not t.get("revoked") and t.get("expires_at", now) >= now
        )
        revoked_tokens = sum(1 for t in self.issued_tokens.values() if t.get("revoked"))
        expired_tokens = sum(
            1
            for t in self.issued_tokens.values()
            if not t.get("revoked") and t.get("expires_at", now) < now
        )

        return {
            "total_issued": len(self.issued_tokens),
            "active": active_tokens,
            "revoked": revoked_tokens,
            "expired": expired_tokens,
        }


# Global instance
_token_handler: Optional[JWTTokenHandler] = None


def get_token_handler(secret_key: Optional[str] = None) -> JWTTokenHandler:
    """Get or create global token handler."""
    global _token_handler
    if _token_handler is None:
        if not secret_key:
            secret_key = secrets.token_urlsafe(32)
        _token_handler = JWTTokenHandler(secret_key)
    return _token_handler
