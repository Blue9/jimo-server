import uuid
from typing import Callable, Optional

from sqlalchemy import select, exists, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import schemas
from models import models


class RelationStore:
    def __init__(self, db: Session):
        self.db = db

    # Scalar queries

    def is_blocked(self, blocked_by_user_id: uuid.UUID, blocked_user_id: uuid.UUID) -> bool:
        """Return whether `blocked_by_user_id` has blocked `blocked_user_id`."""
        query = select(models.UserRelation) \
            .where(models.UserRelation.from_user_id == blocked_by_user_id,
                   models.UserRelation.to_user_id == blocked_user_id,
                   models.UserRelation.relation == models.UserRelationType.blocked)
        return self.db.execute(exists(query).select()).scalar()

    # Operations

    def _try_add_relation(
        self,
        from_user_id: uuid.UUID,
        to_user_id: uuid.UUID,
        relation: models.UserRelationType,
        before_commit: Callable = None
    ) -> Optional[models.UserRelationType]:
        """Try to add the relation, returning the existing relation if one already existed."""
        existing_relation_query = select(models.UserRelation) \
            .where(models.UserRelation.from_user_id == from_user_id,
                   models.UserRelation.to_user_id == to_user_id)
        existing_relation: Optional[models.UserRelation] = self.db.execute(existing_relation_query).scalars().first()
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
        existing_relation_query = delete(models.UserRelation) \
            .where(models.UserRelation.from_user_id == from_user_id,
                   models.UserRelation.to_user_id == to_user_id,
                   models.UserRelation.relation == relation)
        result = self.db.execute(existing_relation_query)
        self.db.commit()
        existing_relation = result.rowcount > 0
        return existing_relation

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
        If from_user (A) blocks to_user (B), make B unfollow A.
        """

        # TODO: race condition 1: If A and B try to block each other at the same time, they could both go through
        #  and they will be unable to unblock each other.
        # TODO: race condition 2: If B follows A after this transaction starts the follow will go through.
        def before_commit():
            query = delete(models.UserRelation) \
                .where(models.UserRelation.from_user_id == to_user_id,
                       models.UserRelation.to_user_id == from_user_id,
                       models.UserRelation.relation == models.UserRelationType.following)
            self.db.execute(query)

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

    def get_relations(
        self,
        from_user_id: uuid.UUID,
        to_user_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, schemas.user.UserRelation]:
        query = select(models.UserRelation.to_user_id, models.UserRelation.relation) \
            .where(models.UserRelation.from_user_id == from_user_id,
                   models.UserRelation.to_user_id.in_(to_user_ids))
        rows = self.db.execute(query).all()
        result = {}
        for to_user_id, relation in rows:
            result[to_user_id] = schemas.user.UserRelation[relation.value]
        return result
