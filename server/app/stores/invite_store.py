import uuid

from sqlalchemy import exists, select, func

from app import config, schemas
from app.db.database import get_db
from app.models import models
from fastapi import Depends
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


class InviteStore:
    def __init__(self, db: Session = Depends(get_db)):
        self.db = db
        self.invites_per_user = config.INVITES_PER_USER

    # Scalar queries

    def is_invited(self, phone_number: str) -> bool:
        """Return whether the phone number has been invited."""
        query = select(models.Invite.id).where(models.Invite.phone_number == phone_number)
        invited = self.db.execute(exists(query).select()).scalar()
        return invited

    def is_on_waitlist(self, phone_number: str) -> bool:
        """Return whether the phone number is on the waitlist."""
        query = select(models.Waitlist.id).where(models.Waitlist.phone_number == phone_number)
        return self.db.execute(exists(query).select()).scalar()

    # Queries

    def num_used_invites(self, user_id: uuid.UUID) -> int:
        query = select(func.count()).select_from(models.Invite).where(models.Invite.invited_by == user_id)
        return self.db.execute(query).scalar()

    # Operations

    def invite_user(
        self,
        invited_by: uuid.UUID,
        phone_number: str,
        ignore_invite_limit: bool = False
    ) -> schemas.invite.UserInviteStatus:
        # Possible race condition if this gets called multiple times for the same user at the same time, bypassing the
        # invite limit. Rate limiting the endpoint based on the auth header should take care of it, plus the worst case
        # is that someone invites extra users which isn't really a problem.
        invite = models.Invite(phone_number=phone_number, invited_by=invited_by)
        self.db.add(invite)
        try:
            self.db.commit()
        except IntegrityError:
            # User already invited
            self.db.rollback()
            return schemas.invite.UserInviteStatus(invited=False, message="User is already invited.")
        return schemas.invite.UserInviteStatus(invited=True)

    def join_waitlist(self, phone_number: str) -> None:
        waitlist_entry = models.Waitlist(phone_number=phone_number)
        self.db.add(waitlist_entry)
        try:
            self.db.commit()
        except IntegrityError:
            # Already on waitlist
            self.db.rollback()
