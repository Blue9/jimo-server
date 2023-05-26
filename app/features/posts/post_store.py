from typing import Optional

import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import jsonb_builder

from app.core.database.helpers import (
    is_unique_constraint_error,
    is_unique_column_error,
    eager_load_post_options,
)
from app.features.images.image_utils import get_images
from app.features.posts.entities import InternalPost, InternalPostSave
from app.core.types import UserId, PostId, PlaceId, CursorId, ImageId
from app.core.database.models import (
    PostRow,
    PostLikeRow,
    PostReportRow,
    PostSaveRow,
)


class PostStore:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def post_exists(
        self, post_id: Optional[PostId] = None, user_id: Optional[UserId] = None, place_id: Optional[PlaceId] = None
    ) -> bool:
        """Return true if a post with the specified params exists."""
        query = sa.select(PostRow.id).where(~PostRow.deleted)
        if post_id is not None:
            query = query.where(PostRow.id == post_id)
        if user_id is not None:
            query = query.where(PostRow.user_id == user_id)
        if place_id is not None:
            query = query.where(PostRow.place_id == place_id)
        result = await self.db.execute(query.exists().select())
        exists: bool = result.scalar()  # type: ignore
        return exists

    async def get_like_count(self, post_id: PostId) -> int:
        """Return the like count of the given post."""
        query = sa.select(sa.func.count()).where(PostLikeRow.post_id == post_id)
        result = await self.db.execute(query)
        like_count: int = result.scalar()  # type: ignore
        return like_count

    async def is_post_liked(self, post_id: PostId, liked_by: UserId) -> bool:
        """Return whether the given post is liked by the given user."""
        query = sa.select(PostLikeRow.id).where(PostLikeRow.post_id == post_id, PostLikeRow.user_id == liked_by)
        result = await self.db.execute(query.exists().select())
        is_liked: bool = result.scalar()  # type: ignore
        return is_liked

    async def get_post(self, post_id: PostId) -> Optional[InternalPost]:
        """Return the post with the given id or None if no such post exists or the post is deleted."""
        post = await self._get_post_row(post_id)
        return InternalPost.from_orm(post) if post else None

    async def get_post_ids(self, user_id: UserId, cursor: Optional[CursorId] = None, limit: int = 50) -> list[PostId]:
        query = sa.select(PostRow.id).where(PostRow.user_id == user_id, ~PostRow.deleted)
        if cursor:
            query = query.where(PostRow.id < cursor)
        query = query.order_by(PostRow.id.desc()).limit(limit)
        result = await self.db.execute(query)
        post_ids = result.scalars().all()
        return post_ids  # type: ignore

    async def get_posts(self, post_ids: list[PostId]) -> dict[PostId, InternalPost]:
        """Get the given posts that aren't deleted."""
        query = (
            sa.select(PostRow)
            .options(*eager_load_post_options())
            .where(PostRow.id.in_(post_ids), ~PostRow.deleted)
            .order_by(PostRow.id.desc())
        )
        result = await self.db.execute(query)
        posts = result.scalars().all()
        return {post.id: InternalPost.from_orm(post) for post in posts}

    async def get_liked_posts(self, user_id: UserId, post_ids: list[PostId]) -> set[PostId]:
        query = sa.select(PostLikeRow.post_id).where(PostLikeRow.user_id == user_id, PostLikeRow.post_id.in_(post_ids))
        result = await self.db.execute(query)
        liked_posts: list[PostId] = result.scalars().all()  # type: ignore
        return set(liked_posts)

    async def get_saved_posts_by_user(
        self, user_id: UserId, cursor: Optional[CursorId], limit: int = 10
    ) -> list[InternalPostSave]:
        """Get the list of saved posts for the given user."""
        query = sa.select(PostSaveRow).where(PostSaveRow.user_id == user_id)
        if cursor:
            query = query.where(PostSaveRow.id < cursor)
        query = query.order_by(PostSaveRow.id.desc()).limit(limit)
        result = await self.db.execute(query)
        saves = result.scalars().all()
        return [InternalPostSave.from_orm(save) for save in saves]

    async def create_post(
        self,
        user_id: UserId,
        place_id: PlaceId,
        category: str,
        content: str,
        media_ids: list[ImageId],
        stars: int | None,
    ) -> InternalPost:
        """Try to create a post with the given details, raising a ValueError if the request is invalid."""
        self._validate_category(category)
        self._validate_stars(stars)  # Already validated by Pydantic but adding extra sanity check
        if await self.post_exists(user_id=user_id, place_id=place_id):
            raise ValueError("You already posted that place.")
        media = await get_images(self.db, user_id, image_ids=media_ids)
        post = PostRow(
            user_id=user_id,
            place_id=place_id,
            category=category,
            content=content,
            image_id=media[0].id if len(media) else None,
            media=jsonb_builder.media_jsonb(media),
            stars=stars,
        )
        try:
            for image in media:
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
                raise ValueError("Could not create post.")

    async def update_post(
        self,
        post_id: PostId,
        place_id: PlaceId,
        category: str,
        content: str,
        media_ids: list[ImageId],
        stars: int | None,
    ) -> InternalPost:
        post: Optional[PostRow] = await self._get_post_row(post_id)
        if post is None:
            raise ValueError("Post does not exist")

        # Update place, category, and content
        self._validate_category(category)
        self._validate_stars(stars)  # Already validated by Pydantic but adding extra sanity check
        post.place_id = place_id
        post.category = category
        post.content = content
        post.stars = stars

        # Update image
        current_image_ids = [media["id"] for media in post.media]
        if media_ids != current_image_ids:
            new_media = await get_images(self.db, post.user_id, image_ids=media_ids)
            post.image_id = new_media[0].id if len(new_media) else None
            post.media = jsonb_builder.media_jsonb(new_media)
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
        """Delete the given post."""
        query = sa.delete(PostRow).where(PostRow.id == post_id)
        await self.db.execute(query)
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
        query = sa.delete(PostLikeRow).where(PostLikeRow.user_id == user_id, PostLikeRow.post_id == post_id)
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
        query = sa.delete(PostSaveRow).where(PostSaveRow.user_id == user_id, PostSaveRow.post_id == post_id)
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

    async def _get_post_row(self, post_id: PostId) -> Optional[PostRow]:
        """Return the post with the given id or None if no such post exists or the post is deleted."""
        query = sa.select(PostRow).options(*eager_load_post_options()).where(PostRow.id == post_id, ~PostRow.deleted)
        result = await self.db.execute(query)
        return result.scalars().first()

    def _validate_category(self, category_name: str) -> None:
        categories = {"food", "cafe", "activity", "attraction", "lodging", "shopping", "nightlife"}
        if category_name not in categories:
            raise ValueError("Invalid category")

    def _validate_stars(self, stars: int | None) -> None:
        if stars is not None and (stars < 0 or stars > 3):
            raise ValueError("Can only award 0-3 stars.")
