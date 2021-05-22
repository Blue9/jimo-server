import uuid
from typing import Callable, Optional

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import schemas
from app.db.database import get_db
from app.models import models


class RelationStore:
    def __init__(self, db: Session = Depends(get_db)):
        self.db = db

    # Scalar queries

    def is_blocked(self, blocked_by_user_id: uuid.UUID, blocked_user_id: uuid.UUID) -> bool:
        """Return whether `blocked_by_user_id` has blocked `blocked_user_id`."""
        query = self.db.query(models.UserRelation) \
            .filter(models.UserRelation.from_user_id == blocked_by_user_id,
                    models.UserRelation.to_user_id == blocked_user_id,
                    models.UserRelation.relation == models.UserRelationType.blocked) \
            .exists()
        return self.db.query(query).scalar()

    # Operations

    def _try_add_relation(
        self,
        from_user_id: uuid.UUID,
        to_user_id: uuid.UUID,
        relation: models.UserRelationType,
        before_commit: Callable = None
    ) -> Optional[models.UserRelationType]:
        """Try to add the relation, returning the existing relation if one already existed."""
        existing_relation: Optional[models.UserRelation] = self.db.query(models.UserRelation) \
            .filter(models.UserRelation.from_user_id == from_user_id,
                    models.UserRelation.to_user_id == to_user_id) \
            .first()
        if existing_relation:
            return existing_relation.relation
        # else:
        relation = models.UserRelation(from_user_id=from_user_id, to_user_id=to_user_id, relation=relation)
        self.db.add(relation)
        try:
            if before_commit:
                before_commit()
            self.db.commit()
            return None
        except IntegrityError:
            self.db.rollback()
            # Most likely we inserted in another request between querying and inserting
            raise ValueError("Could not complete request")

    def _remove_relation(
        self,
        from_user_id: uuid.UUID,
        to_user_id: uuid.UUID,
        relation: models.UserRelationType
    ) -> bool:
        """Try to remove the relation, returning true if the relation was deleted and false if it didn't exist."""
        existing_relation = self.db.query(models.UserRelation) \
            .filter(models.UserRelation.from_user_id == from_user_id,
                    models.UserRelation.to_user_id == to_user_id,
                    models.UserRelation.relation == relation) \
            .delete()
        self.db.commit()
        return existing_relation > 0

    def follow_user(self, from_user_id: uuid.UUID, to_user_id: uuid.UUID):
        existing = self._try_add_relation(from_user_id, to_user_id, models.UserRelationType.following)
        if existing == models.UserRelationType.following:
            raise ValueError("Already following user")
        elif existing == models.UserRelationType.blocked:
            raise ValueError("Cannot follow someone you blocked")

    def unfollow_user(self, from_user_id: uuid.UUID, to_user_id: uuid.UUID):
        unfollowed = self._remove_relation(from_user_id, to_user_id, models.UserRelationType.following)
        if not unfollowed:
            raise ValueError("Not following user")

    def block_user(self, from_user_id: uuid.UUID, to_user_id: uuid.UUID) -> schemas.base.SimpleResponse:
        """
        Have from_user block to_user.

        Requires that from_user does not already follow or block to_user.
        If from_user (A) blocks to_user (B), make B unfollow A, and remove their likes from each other's posts.
        """

        # TODO: race condition 1: If A and B try to block each other at the same time, they could both go through
        #  and they will be unable to unblock each other.
        # TODO: race condition 2: If B follows A after this transaction starts the follow will go through.
        # TODO: race condition 3: If A/B likes B/A's post after this transaction starts, the inner select stmt won't
        #  detect it, so that like will remain un-deleted.
        def before_commit():
            self.db.query(models.UserRelation) \
                .filter(models.UserRelation.from_user_id == to_user_id,
                        models.UserRelation.to_user_id == from_user_id,
                        models.UserRelation.relation == models.UserRelationType.following) \
                .delete()
            # Delete to_user's likes of from_user's posts
            self.db.query(models.PostLike) \
                .filter(models.PostLike.user_id == to_user_id,
                        models.PostLike.post_id.in_(
                            select([models.Post.id]).where(models.Post.user_id == from_user_id))) \
                .delete(synchronize_session=False)
            # Delete from_user's likes of to_user's posts
            self.db.query(models.PostLike) \
                .filter(models.PostLike.user_id == from_user_id,
                        models.PostLike.post_id.in_(
                            select([models.Post.id]).where(models.Post.user_id == to_user_id))) \
                .delete(synchronize_session=False)

        existing = self._try_add_relation(from_user_id, to_user_id, models.UserRelationType.blocked,
                                          before_commit=before_commit)
        if existing == models.UserRelationType.following:
            raise ValueError("Cannot block someone you follow")
        elif existing == models.UserRelationType.blocked:
            raise ValueError("Already blocked")
        else:  # existing is None
            return schemas.base.SimpleResponse(success=True)

    def unblock_user(self, from_user_id: uuid.UUID, to_user_id: uuid.UUID) -> schemas.base.SimpleResponse:
        unblocked = self._remove_relation(from_user_id, to_user_id, models.UserRelationType.blocked)
        if unblocked:
            return schemas.base.SimpleResponse(success=True)
        else:
            raise ValueError("Not blocked")
