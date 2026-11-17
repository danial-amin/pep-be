"""
Invite-only authentication service.
"""
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import hash_password, verify_password, create_access_token
from app.models.user import User, Invite
from app.models.project import Project

logger = logging.getLogger(__name__)


class AuthService:
    @staticmethod
    async def count_users(session: AsyncSession) -> int:
        result = await session.execute(select(func.count()).select_from(User))
        return int(result.scalar() or 0)

    @staticmethod
    async def get_user_by_email(session: AsyncSession, email: str) -> Optional[User]:
        result = await session.execute(
            select(User).where(User.email == email.lower().strip())
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_by_id(session: AsyncSession, user_id: int) -> Optional[User]:
        result = await session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def authenticate(session: AsyncSession, email: str, password: str) -> Optional[User]:
        user = await AuthService.get_user_by_email(session, email)
        if not user or not user.is_active:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    @staticmethod
    def issue_token(user: User) -> str:
        return create_access_token(
            subject=str(user.id),
            extra={"email": user.email, "is_admin": user.is_admin},
        )

    @staticmethod
    async def bootstrap_admin_if_needed(session: AsyncSession) -> Optional[User]:
        """Create first admin from env when no users exist."""
        count = await AuthService.count_users(session)
        if count > 0:
            return None

        email = (settings.ADMIN_EMAIL or "").strip().lower()
        password = settings.ADMIN_PASSWORD or ""
        if not email or not password:
            logger.warning(
                "No users in DB and ADMIN_EMAIL/ADMIN_PASSWORD not set — "
                "invite-only auth has no bootstrap admin yet."
            )
            return None

        admin = User(
            email=email,
            name=settings.ADMIN_NAME or "Admin",
            hashed_password=hash_password(password),
            is_admin=True,
            is_active=True,
        )
        session.add(admin)
        await session.flush()

        # Assign orphan projects to the bootstrap admin
        result = await session.execute(
            select(Project).where(Project.user_id.is_(None))
        )
        for project in result.scalars().all():
            project.user_id = admin.id

        await session.commit()
        await session.refresh(admin)
        logger.info("Bootstrapped admin user %s (id=%s)", admin.email, admin.id)
        return admin

    @staticmethod
    async def create_invite(
        session: AsyncSession,
        email: str,
        invited_by: User,
        note: Optional[str] = None,
        expires_in_days: Optional[int] = None,
    ) -> Invite:
        email_norm = email.lower().strip()
        existing = await AuthService.get_user_by_email(session, email_norm)
        if existing:
            raise ValueError("A user with this email already exists")

        days = expires_in_days or settings.INVITE_EXPIRE_DAYS
        invite = Invite(
            email=email_norm,
            token=secrets.token_urlsafe(32),
            invited_by_id=invited_by.id,
            expires_at=datetime.now(timezone.utc) + timedelta(days=days),
            note=note,
        )
        session.add(invite)
        await session.flush()
        await session.refresh(invite)
        return invite

    @staticmethod
    async def list_invites(session: AsyncSession) -> List[Invite]:
        result = await session.execute(
            select(Invite).order_by(Invite.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_invite_by_token(session: AsyncSession, token: str) -> Optional[Invite]:
        result = await session.execute(select(Invite).where(Invite.token == token))
        return result.scalar_one_or_none()

    @staticmethod
    def invite_is_valid(invite: Invite) -> Tuple[bool, str]:
        if invite.accepted_at is not None:
            return False, "Invite already accepted"
        expires = invite.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires < datetime.now(timezone.utc):
            return False, "Invite expired"
        return True, ""

    @staticmethod
    async def accept_invite(
        session: AsyncSession,
        token: str,
        name: str,
        password: str,
    ) -> User:
        invite = await AuthService.get_invite_by_token(session, token)
        if not invite:
            raise ValueError("Invalid invite token")

        ok, reason = AuthService.invite_is_valid(invite)
        if not ok:
            raise ValueError(reason)

        existing = await AuthService.get_user_by_email(session, invite.email)
        if existing:
            raise ValueError("A user with this email already exists")

        user = User(
            email=invite.email,
            name=name.strip(),
            hashed_password=hash_password(password),
            is_admin=False,
            is_active=True,
        )
        session.add(user)
        await session.flush()

        invite.accepted_at = datetime.now(timezone.utc)
        await session.flush()
        await session.refresh(user)
        return user
