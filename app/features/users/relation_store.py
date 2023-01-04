from typing import Callable, Optional, Awaitable

import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.types import UserId, UserRelationId, CursorId
from app.features.users.entities import UserRelation
from app.core.database.models import UserRelationType, UserRelationRow


class RelationStore:
    def __init__(self, db: AsyncSession):
        self.db = db

    # Scalar query

    async def is_blocked(self, blocked_by_user_id: UserId, blocked_user_id: UserId) -> bool:
        """Return whether `blocked_by_user_id` has blocked `blocked_user_id`."""
        query = sa.select(UserRelationRow.id).where(
            UserRelationRow.relation == UserRelationType.blocked,
            UserRelationRow.from_user_id == blocked_by_user_id,
            UserRelationRow.to_user_id == blocked_user_id,
        )
        result = await self.db.execute(query.exists().select())
        is_blocked: bool = result.scalar()  # type: ignore
        return is_blocked

    async def get_followers(
        self, user_id: UserId, before_id: Optional[UserRelationId] = None, limit: int = 25
    ) -> tuple[list[UserId], Optional[CursorId]]:
        query = sa.select(UserRelationRow).where(
            UserRelationRow.relation == UserRelationType.following, UserRelationRow.to_user_id == user_id
        )
        if before_id:
            query = query.where(UserRelationRow.id < before_id)
        query = query.order_by(UserRelationRow.id.desc()).limit(limit)
        result = await self.db.execute(query)
        rows = result.scalars().all()
        user_ids: list[UserId] = [row.from_user_id for row in rows]
        cursor = rows[-1].id if len(rows) == limit else None
        return user_ids, cursor

    async def get_following(
        self, user_id: UserId, before_id: Optional[UserRelationId] = None, limit: int = 25
    ) -> tuple[list[UserId], Optional[CursorId]]:
        query = sa.select(UserRelationRow).where(
            UserRelationRow.relation == UserRelationType.following, UserRelationRow.from_user_id == user_id
        )
        if before_id:
            query = query.where(UserRelationRow.id < before_id)
        query = query.order_by(UserRelationRow.id.desc()).limit(limit)
        result = await self.db.execute(query)
        rows = result.scalars().all()
        user_ids: list[UserId] = [row.to_user_id for row in rows]
        cursor = rows[-1].id if len(rows) == limit else None
        return user_ids, cursor

    async def get_relations(self, from_user_id: UserId, to_user_ids: list[UserId]) -> dict[UserId, UserRelation]:
        query = sa.select(UserRelationRow).where(
            UserRelationRow.from_user_id == from_user_id, UserRelationRow.to_user_id.in_(to_user_ids)
        )
        result = await self.db.execute(query)
        rows = result.scalars().all()
        return {row.to_user_id: UserRelation[row.relation.value] for row in rows}

    async def follow_user(self, from_user_id: UserId, to_user_id: UserId) -> None:
        existing = await self._try_add_relation(from_user_id, to_user_id, UserRelationType.following)
        if existing == UserRelationType.following:
            raise ValueError("Already following user")
        elif existing == UserRelationType.blocked:
            raise ValueError("Cannot follow someone you blocked")

    async def unfollow_user(self, from_user_id: UserId, to_user_id: UserId) -> None:
        unfollowed = await self._remove_relation(from_user_id, to_user_id, UserRelationType.following)
        if not unfollowed:
            raise ValueError("Not following user")

    async def block_user(self, from_user_id: UserId, to_user_id: UserId) -> None:
        """
        Have from_user block to_user.

        Requires that from_user does not already follow or block to_user.
        If from_user (A) blocks to_user (B), make B unfollow A.
        """

        # TODO: race condition 1: If A and B try to block each other at the same time, they could both go through
        #  and they will be unable to unblock each other.
        # TODO: race condition 2: If B follows A after this transaction starts the follow will go through.
        async def before_commit() -> None:
            query = sa.delete(UserRelationRow).where(
                UserRelationRow.from_user_id == to_user_id,
                UserRelationRow.to_user_id == from_user_id,
                UserRelationRow.relation == UserRelationType.following,
            )
            await self.db.execute(query)

        existing = await self._try_add_relation(
            from_user_id,
            to_user_id,
            UserRelationType.blocked,
            before_commit=before_commit,
        )
        if existing == UserRelationType.following:
            raise ValueError("Cannot block someone you follow")
        elif existing == UserRelationType.blocked:
            raise ValueError("Already blocked")

    async def unblock_user(self, from_user_id: UserId, to_user_id: UserId) -> None:
        did_unblock = await self._remove_relation(from_user_id, to_user_id, UserRelationType.blocked)
        if not did_unblock:
            raise ValueError("Not blocked")

    # Helpers

    async def _try_add_relation(
        self,
        from_user_id: UserId,
        to_user_id: UserId,
        relation_type: UserRelationType,
        before_commit: Optional[Callable[[], Awaitable[None]]] = None,
    ) -> Optional[UserRelationType]:
        """Try to add the relation, returning the existing relation if one already exists."""
        query = sa.select(UserRelationRow.relation).where(
            UserRelationRow.from_user_id == from_user_id, UserRelationRow.to_user_id == to_user_id
        )
        result = await self.db.execute(query)
        existing_relation: Optional[UserRelationType] = result.scalars().first()
        if existing_relation:
            return existing_relation
        # else:
        relation = UserRelationRow(from_user_id=from_user_id, to_user_id=to_user_id, relation=relation_type)
        self.db.add(relation)
        try:
            if before_commit:
                await before_commit()
            await self.db.commit()
            return None
        except IntegrityError:
            await self.db.rollback()
            # Most likely we inserted in another request between querying and inserting
            raise ValueError("Could not complete request")

    async def _remove_relation(self, from_user_id: UserId, to_user_id: UserId, relation: UserRelationType) -> bool:
        """Try to remove the relation, returning true if the relation was deleted and false if it didn't exist."""
        delete_query = sa.delete(UserRelationRow).where(
            UserRelationRow.from_user_id == from_user_id,
            UserRelationRow.to_user_id == to_user_id,
            UserRelationRow.relation == relation,
        )
        result = await self.db.execute(delete_query)
        await self.db.commit()
        did_delete_relation: bool = result.rowcount > 0  # type: ignore
        return did_delete_relation
