from typing import Optional

from sqlalchemy import select, exists, update, func, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.helpers import (
    get_image_with_lock_else_throw,
    is_unique_constraint_error,
    is_unique_column_error,
)
from app.core.internal import InternalPost, InternalPostSave
from app.core.types import UserId, PostId, PlaceId, CursorId, ImageId
from app.core.database.models import (
    CategoryRow,
    PostRow,
    PostLikeRow,
    PostReportRow,
    PostSaveRow,
)
from app.features.map.filters import CategoryFilter, MapFilter
from app.core.database.complex_queries import posts_for_pin_v3_query
from app.features.posts.post_like_query import PostLikeQuery
from app.features.posts.post_query import PostQuery
from app.features.posts.post_save_query import PostSaveQuery


class PostStore:
    def __init__(self, db: AsyncSession):
        self.db = db

    # Scalar query
    async def already_posted(self, user_id: UserId, place_id: PlaceId) -> bool:
        """Return true if the user already posted this place, false otherwise."""
        return await PostQuery().user_id(user_id).place_id(place_id).execute_exists(self.db, include_deleted=False)

    async def get_like_count(self, post_id: PostId) -> int:
        """Return the like count of the given post."""
        return await PostLikeQuery(func.count()).post_id(post_id).execute_scalar(self.db)  # type: ignore

    async def post_exists_and_not_deleted(self, post_id: PostId) -> bool:
        """Return whether the post exists and is not deleted."""
        return await PostQuery().post_id(post_id).execute_exists(self.db, include_deleted=False)

    async def is_post_liked(self, post_id: PostId, liked_by: UserId) -> bool:
        """Return whether the given post is liked by the given user."""
        return await PostLikeQuery().post_id(post_id).liked_by(liked_by).execute_exists(self.db)

    async def is_post_saved(self, post_id: PostId, saved_by: UserId) -> bool:
        """Return whether the given post is saved by the given user."""
        return await PostSaveQuery().post_id(post_id).saved_by(saved_by).execute_exists(self.db)

    # Queries

    async def get_post(self, post_id: PostId) -> Optional[InternalPost]:
        """Return the post with the given id or None if no such post exists or the post is deleted."""
        post = await PostQuery().post_id(post_id).execute_one(self.db)
        return InternalPost.from_orm(post) if post else None

    async def get_post_ids(self, user_id: UserId, cursor: Optional[CursorId] = None, limit: int = 50) -> list[PostId]:
        return (
            await PostQuery(PostRow.id)
            .user_id(user_id)
            .cursor(cursor)
            .order_by(PostRow.id.desc())
            .limit(limit)
            .execute_many(self.db)
        )

    async def get_posts(self, post_ids: list[PostId], preserve_order: bool = False) -> list[InternalPost]:
        """Get the given posts that aren't deleted."""
        posts = await PostQuery().post_id_in(post_ids).order_by(PostRow.id.desc()).execute_many(self.db)
        if preserve_order:
            post_indices = {post_id: i for i, post_id in enumerate(post_ids)}
            posts = sorted(posts, key=lambda post: post_indices[post.id])
        return [InternalPost.from_orm(post) for post in posts]

    async def get_liked_posts(self, user_id: UserId, post_ids: list[PostId]) -> set[PostId]:
        post_ids = await PostQuery(PostRow.id).post_id_in(post_ids).liked_by_user(user_id).execute_many(self.db)
        return set(post_ids)

    async def get_saved_posts(self, user_id: UserId, post_ids: list[PostId]) -> set[PostId]:
        post_ids = await PostQuery(PostRow.id).post_id_in(post_ids).saved_by_user(user_id).execute_many(self.db)
        return set(post_ids)

    async def get_mutual_posts_v3(
        self,
        place_id: PlaceId,
        user_filter: MapFilter,
        category_filter: CategoryFilter,
        limit: int = 50,
    ) -> list[PostId]:
        query = posts_for_pin_v3_query(place_id, user_filter, category_filter, limit=limit)
        result = await self.db.execute(query)
        post_ids = result.scalars().all()
        return post_ids

    async def get_saved_posts_by_user(
        self, user_id: UserId, cursor: Optional[CursorId], limit: int = 10
    ) -> list[InternalPostSave]:
        """Get the list of saved posts for the given user."""
        saves = (
            await PostSaveQuery()
            .saved_by(user_id)
            .cursor(cursor)
            .order_by(PostSaveRow.id.desc())
            .limit(limit)
            .execute_many(self.db)
        )
        return [InternalPostSave.from_orm(save) for save in saves]

    # Operations

    async def create_post(
        self,
        user_id: UserId,
        place_id: PlaceId,
        category: str,
        content: str,
        image_id: Optional[ImageId],
    ) -> InternalPost:
        """Try to create a post with the given details, raising a ValueError if the request is invalid."""
        category = await self._get_category_or_raise(category)
        if await self.already_posted(user_id, place_id):
            raise ValueError("You already posted that place.")
        image = await get_image_with_lock_else_throw(self.db, user_id, image_id) if image_id is not None else None
        post = PostRow(
            user_id=user_id,
            place_id=place_id,
            category=category,
            content=content,
            image_id=image.id if image else None,
        )
        try:
            if image:
                image.used = True
            self.db.add(post)
            await self.db.commit()
            await self.db.refresh(post, ["id"])
            created_post = await self.get_post(post.id)
            if created_post is None:
                raise ValueError("Created post but failed to retrieve it.")
            return created_post
        except IntegrityError as e:
            await self.db.rollback()
            if is_unique_constraint_error(e, PostRow.user_place_uc):
                raise ValueError("You already posted that place.")
            elif is_unique_column_error(e, PostRow.image_id.key):
                raise ValueError("Duplicate image.")
            else:
                print(e)
                raise ValueError("Could not create post.")

    async def update_post(
        self,
        post_id: PostId,
        place_id: PlaceId,
        category: str,
        content: str,
        image_id: Optional[ImageId],
    ) -> InternalPost:
        post: Optional[PostRow] = await PostQuery().post_id(post_id).execute_one(self.db)
        if post is None:
            raise ValueError("Post does not exist")

        # Update place, category, and content
        post.place_id = place_id
        post.category = await self._get_category_or_raise(category)
        post.content = content

        # Update image
        if image_id != post.image_id:
            if image_id:
                image = await get_image_with_lock_else_throw(self.db, post.user_id, image_id)
                image.used = True
            post.image_id = image_id
        try:
            await self.db.commit()
        except IntegrityError as e:
            await self.db.rollback()
            if is_unique_constraint_error(e, PostRow.user_place_uc):
                raise ValueError("You already posted that place.")
            elif is_unique_column_error(e, PostRow.image_id.key):
                raise ValueError("Duplicate image.")
            else:
                raise ValueError("Could not update post.")
        updated_post = await self.get_post(post_id)
        if updated_post is None:
            raise ValueError("Can't find post.")
        return updated_post

    async def delete_post(self, post_id: PostId) -> None:
        """Mark the given post as deleted."""
        await self.db.execute(update(PostRow).where(PostRow.id == post_id).values(deleted=True))
        await self.db.commit()

    async def like_post(self, user_id: UserId, post_id: PostId) -> None:
        """Like the given post."""
        post_like = PostLikeRow(user_id=user_id, post_id=post_id)
        self.db.add(post_like)
        try:
            await self.db.commit()
        except IntegrityError:
            # Ignore error when trying to like a post twice
            await self.db.rollback()
            return

    async def unlike_post(self, user_id: UserId, post_id: PostId) -> None:
        """Unlike the given post."""
        query = delete(PostLikeRow).where(PostLikeRow.user_id == user_id, PostLikeRow.post_id == post_id)
        await self.db.execute(query)
        await self.db.commit()

    async def save_post(self, user_id: UserId, post_id: PostId) -> None:
        """Add the given post to the user's saved posts."""
        post_save = PostSaveRow(user_id=user_id, post_id=post_id)
        self.db.add(post_save)
        try:
            await self.db.commit()
        except IntegrityError:
            # Ignore error when trying to save a post twice
            await self.db.rollback()
            return

    async def unsave_post(self, user_id: UserId, post_id: PostId) -> None:
        """Remove the given post from the user's saved posts."""
        query = delete(PostSaveRow).where(PostSaveRow.user_id == user_id, PostSaveRow.post_id == post_id)
        await self.db.execute(query)
        await self.db.commit()

    async def report_post(self, post_id: PostId, reported_by: UserId, details: Optional[str]) -> bool:
        # TODO(gautam): This should probably just raise if it fails
        report = PostReportRow(post_id=post_id, reported_by_user_id=reported_by, details=details)
        try:
            self.db.add(report)
            await self.db.commit()
            return True
        except IntegrityError:
            await self.db.rollback()
            return False

    async def _get_category_or_raise(self, category_name: str) -> str:
        """Get the category object for the given category name."""
        query = select(CategoryRow).where(CategoryRow.name == category_name)
        category = (await self.db.execute(exists(query).select())).scalar()
        if not category:
            raise ValueError("Invalid category")
        return category_name
