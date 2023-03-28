import enum
from typing import Any

from geoalchemy2 import Geography  # type: ignore
from sqlalchemy import (
    Enum,
    DateTime,
    Boolean,
    ForeignKey,
    Integer,
    Text,
    select,
    func,
    Float,
    Computed,
    UniqueConstraint,
    Index,
    false,
    true,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.orm import (
    relationship,
    column_property,
    aliased,
    declarative_base,
    Mapped,
    mapped_column,
)
from sqlalchemy.sql import expression
from app.core.database.defaults import gen_ulid


Base: Any = declarative_base()


class LocationPingRow(Base):
    __tablename__ = "location"
    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=gen_ulid)
    uid = mapped_column(Text, nullable=False)
    latitude = mapped_column(Float, nullable=False)
    longitude = mapped_column(Float, nullable=False)
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


# region Users
class UserRelationType(enum.Enum):
    following = "following"
    blocked = "blocked"


class UserRelationRow(Base):
    __tablename__ = "follow"

    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=gen_ulid)
    from_user_id = mapped_column(UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    to_user_id = mapped_column(UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    relation = mapped_column(Enum(UserRelationType), nullable=False)
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("from_user_id", "to_user_id", name="_from_user_to_user_uc"),
        Index("user_relation_to_user_id_relation_idx", to_user_id, relation),
        Index("user_relation_from_user_id_relation_idx", from_user_id, relation),
    )


class UserRow(Base):
    __tablename__ = "user"

    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=gen_ulid)
    uid = mapped_column(Text, unique=True, nullable=False)  # Firebase id, maps to Firebase users
    username = mapped_column(Text, unique=True, nullable=False)
    first_name = mapped_column(Text, nullable=False)
    last_name = mapped_column(Text, nullable=False)
    phone_number = mapped_column(Text, unique=True, nullable=True)
    profile_picture_id = mapped_column(UUID(as_uuid=True), ForeignKey("image_upload.id"), unique=True, nullable=True)
    is_featured = mapped_column(Boolean, nullable=False, server_default=false())
    is_admin = mapped_column(Boolean, nullable=False, server_default=expression.false())
    deleted = mapped_column(Boolean, nullable=False, server_default=expression.false())
    username_lower = mapped_column(Text, Computed("LOWER(username)"), unique=True, nullable=False)
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    onboarded_at = mapped_column(DateTime(timezone=True), nullable=True)
    onboarded_city = mapped_column(Text, nullable=True)
    updated_at = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    profile_picture: Mapped["ImageUploadRow"] = relationship(
        "ImageUploadRow",
        primaryjoin="UserRow.profile_picture_id == ImageUploadRow.id",
    )
    profile_picture_url = association_proxy("profile_picture", "url")
    profile_picture_blob_name = association_proxy("profile_picture", "blob_name")

    # Computed column properties (set at end of file)
    # post_count: Mapped[int]
    # follower_count: Mapped[int]
    # following_count: Mapped[int]


class FCMTokenRow(Base):
    __tablename__ = "fcm_token"

    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=gen_ulid)
    user_id = mapped_column(UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    token = mapped_column(Text, nullable=False)
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (UniqueConstraint("user_id", "token", name="_user_token"),)


class UserPrefsRow(Base):
    __tablename__ = "preferences"

    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=gen_ulid)
    user_id = mapped_column(UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    follow_notifications = mapped_column(Boolean, nullable=False, server_default=true())
    post_liked_notifications = mapped_column(Boolean, nullable=False, server_default=true())
    comment_notifications = mapped_column(Boolean, nullable=False, server_default=true())
    comment_liked_notifications = mapped_column(Boolean, nullable=False, server_default=true())
    searchable_by_phone_number = mapped_column(Boolean, nullable=False, server_default=true())
    post_notifications = mapped_column(Boolean, nullable=False, server_default=true())
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    user: Mapped[UserRow] = relationship(UserRow)


# endregion Users

# region Categories
class CategoryRow(Base):
    __tablename__ = "category"

    name = mapped_column(Text, primary_key=True)


# endregion Categories

# region Places
class PlaceRow(Base):
    __tablename__ = "place"

    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=gen_ulid)
    name = mapped_column(Text, nullable=False)

    # Latitude and longitude of the place
    # This might be the entrance of the place, the most visited location, etc.
    # NOT necessarily the geometric centroid of the place
    latitude = mapped_column(Float, nullable=False)
    longitude = mapped_column(Float, nullable=False)

    # Computed column for postgis, don't manually modify; modify the above columns instead
    location = mapped_column(
        Geography(geometry_type="POINT", srid=4326, spatial_index=False),
        Computed("ST_MakePoint(longitude, latitude)::geography"),
        nullable=False,
    )

    city = mapped_column(Text, nullable=True)
    category = mapped_column(Text, nullable=True)

    # Computed column property (set at end of file)

    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Only want one row per (name, latitude, longitude)
    __table_args__ = (
        UniqueConstraint("name", "latitude", "longitude", name="_place_name_location"),
        Index("idx_place_location", location, postgresql_using="gist"),
    )


class PlaceSaveRow(Base):
    """
    Saved places by users.
    """

    __tablename__ = "place_save"
    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=gen_ulid)
    user_id = mapped_column(UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    place_id = mapped_column(UUID(as_uuid=True), ForeignKey("place.id", ondelete="CASCADE"), nullable=False)
    # TODO remove category, this is only temporary as we migrate from saved posts to saved places
    category = mapped_column(Text, ForeignKey("category.name"), nullable=True)
    note = mapped_column(Text, nullable=False)
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    place: Mapped[PlaceRow] = relationship("PlaceRow", primaryjoin="PlaceSaveRow.place_id == PlaceRow.id")

    __table_args__ = (
        UniqueConstraint(user_id, place_id, name="_place_save_user_place_uc"),
        Index("idx_place_save_place_id", place_id),
    )


class PlaceDataRow(Base):
    """
    Crowd-sourced place data.
    """

    __tablename__ = "place_data"

    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=gen_ulid)
    user_id = mapped_column(UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    place_id = mapped_column(UUID(as_uuid=True), ForeignKey("place.id", ondelete="CASCADE"), nullable=False)

    # Region that describes the boundary of the place
    # Used to deduplicate places
    region_center_lat = mapped_column(Float, nullable=True)
    region_center_long = mapped_column(Float, nullable=True)
    radius_meters = mapped_column(Float, nullable=True)

    # Additional data like business url, phone number, point of interest categories, etc.
    additional_data = mapped_column(JSONB, nullable=True)

    # Computed column for postgis, don't manually modify; modify the above columns instead
    region_center = mapped_column(
        Geography(geometry_type="POINT", srid=4326, spatial_index=False),
        Computed("ST_MakePoint(region_center_long, region_center_lat)::geography"),
    )
    region = mapped_column(
        Geography(geometry_type="POLYGON", srid=4326, spatial_index=False),
        Computed("ST_Buffer(ST_MakePoint(region_center_long, region_center_lat)::geography, radius_meters, 100)"),
    )
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    place: Mapped[PlaceRow] = relationship("PlaceRow", primaryjoin="PlaceDataRow.place_id == PlaceRow.id")

    # Only want one row per (user, place) pair
    __table_args__ = (
        UniqueConstraint("user_id", "place_id", name="_place_data_user_place_uc"),
        Index("idx_place_data_region", region, postgresql_using="gist"),
        Index("idx_place_data_region_center", region_center, postgresql_using="gist"),
    )


# endregion Places

# region Posts
class PostRow(Base):
    __tablename__ = "post"

    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=gen_ulid)
    user_id = mapped_column(UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    place_id = mapped_column(UUID(as_uuid=True), ForeignKey("place.id"), nullable=False)
    category = mapped_column(Text, ForeignKey("category.name"), nullable=False)

    content = mapped_column(Text, nullable=False)
    # image_id is deprecated, use media
    image_id = mapped_column(UUID(as_uuid=True), ForeignKey("image_upload.id"), unique=True, nullable=True)
    media = mapped_column(JSONB, nullable=False, server_default="[]")  # list[MediaEntity]
    stars = mapped_column(Integer, nullable=True)
    deleted = mapped_column(Boolean, nullable=False, server_default=expression.false())
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    user: Mapped[UserRow] = relationship("UserRow")
    place: Mapped[PlaceRow] = relationship("PlaceRow")
    image: "Mapped[ImageUploadRow | None]" = relationship("ImageUploadRow")

    image_url = association_proxy("image", "url")
    image_blob_name = association_proxy("image", "blob_name")

    # Computed column properties (set at end of file)
    # like_count: Mapped[int]
    # comment_count: Mapped[int]

    # Only want one row per (user, place) pair for all non-deleted posts
    user_place_uc = "_posts_user_place_uc"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "place_id",
            name=user_place_uc,
        ),
        Index("idx_post_place_id", "place_id"),
    )


class PostLikeRow(Base):
    __tablename__ = "post_like"

    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=gen_ulid)
    user_id = mapped_column(UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    post_id = mapped_column(UUID(as_uuid=True), ForeignKey("post.id", ondelete="CASCADE"), nullable=False)
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    liked_by: Mapped[UserRow] = relationship("UserRow")

    # Only want one row per (user, post) pair
    __table_args__ = (
        UniqueConstraint("user_id", "post_id", name="_post_like_user_post_uc"),
        Index("post_like_post_id_idx", post_id),
    )


class PostSaveRow(Base):
    __tablename__ = "post_save"

    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=gen_ulid)
    user_id = mapped_column(UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    post_id = mapped_column(UUID(as_uuid=True), ForeignKey("post.id", ondelete="CASCADE"), nullable=False)
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    saved_by: Mapped[UserRow] = relationship("UserRow")

    # Only want one row per (user, post) pair
    __table_args__ = (
        UniqueConstraint("user_id", "post_id", name="_saved_post_user_post_uc"),
        Index("saved_post_user_id_idx", user_id),
    )


class PostReportRow(Base):
    __tablename__ = "post_report"

    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=gen_ulid)
    post_id = mapped_column(UUID(as_uuid=True), ForeignKey("post.id", ondelete="CASCADE"), nullable=False)
    reported_by_user_id = mapped_column(UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    details = mapped_column(Text, nullable=True)
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    post: Mapped[PostRow] = relationship("PostRow")
    reported_by: Mapped[UserRow] = relationship("UserRow")

    # Can only report a post once
    __table_args__ = (UniqueConstraint("post_id", "reported_by_user_id", name="_report_post_user_uc"),)


# endregion Posts

# region Comments


class CommentLikeRow(Base):
    __tablename__ = "comment_like"

    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=gen_ulid)
    user_id = mapped_column(UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    comment_id = mapped_column(UUID(as_uuid=True), ForeignKey("comment.id", ondelete="CASCADE"), nullable=False)
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Only want one row per (user, comment) pair
    __table_args__ = (UniqueConstraint("user_id", "comment_id", name="_comment_like_user_post_uc"),)


class CommentRow(Base):
    __tablename__ = "comment"

    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=gen_ulid)
    user_id = mapped_column(UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    post_id = mapped_column(UUID(as_uuid=True), ForeignKey("post.id", ondelete="CASCADE"), nullable=False)
    content = mapped_column(Text, nullable=False)
    deleted = mapped_column(Boolean, nullable=False, server_default=expression.false())

    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    user: Mapped[UserRow] = relationship("UserRow")

    # Computed column properties (set at end of file)
    # like_count: Mapped[int]

    __table_args__ = (Index("comment_post_id_idx", post_id),)


# endregion Comments


class ImageUploadRow(Base):
    __tablename__ = "image_upload"

    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=gen_ulid)
    user_id = mapped_column(UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    blob_name = mapped_column(Text, nullable=True)  # Set after creating the row in db
    url = mapped_column(Text, nullable=True)  # Set after creating the row in db
    used = mapped_column(
        Boolean, nullable=False, server_default=false()
    )  # Prevent using the same image in different places
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class FeedbackRow(Base):
    __tablename__ = "feedback"
    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=gen_ulid)
    user_id = mapped_column(UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    contents = mapped_column(Text, nullable=False)
    follow_up = mapped_column(Boolean, nullable=False, server_default=expression.false())
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    user: Mapped[UserRow] = relationship("UserRow")


# Column properties

# Need aliases so multiple properties on the same model don't interfere and mess up the joins
PostRowAlias = aliased(PostRow)
RelationRowAlias = aliased(UserRelationRow)
PostLikeAlias = aliased(PostLikeRow)

# Users
UserRow.post_count = column_property(
    select(func.count()).where(PostRowAlias.user_id == UserRow.id, ~PostRowAlias.deleted).scalar_subquery(),
    deferred=True,
)

UserRow.follower_count = column_property(
    select(func.count())
    .select_from(RelationRowAlias)
    .where(
        RelationRowAlias.to_user_id == UserRow.id,
        RelationRowAlias.relation == UserRelationType.following,
    )
    .scalar_subquery(),
    deferred=True,
)

UserRow.following_count = column_property(
    select(func.count())
    .select_from(RelationRowAlias)
    .where(
        RelationRowAlias.from_user_id == UserRow.id,
        RelationRowAlias.relation == UserRelationType.following,
    )
    .scalar_subquery(),
    deferred=True,
)

# Posts
PostRow.like_count = column_property(
    select(func.count()).select_from(PostLikeAlias).where(PostRow.id == PostLikeAlias.post_id).scalar_subquery(),
    deferred=True,
)

PostRow.comment_count = column_property(
    select(func.count())
    .select_from(CommentRow)
    .where(PostRow.id == CommentRow.post_id, ~CommentRow.deleted)
    .scalar_subquery(),
    deferred=True,
)

# Comments
CommentRow.like_count = column_property(
    select(func.count())
    .select_from(CommentLikeRow)
    .where(CommentRow.id == CommentLikeRow.comment_id)
    .scalar_subquery(),
    deferred=True,
)
