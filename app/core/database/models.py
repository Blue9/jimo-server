import enum
import uuid
from typing import Any, Optional

from geoalchemy2 import Geography  # type: ignore
from sqlalchemy import (
    Column,
    Enum,
    DateTime,
    Boolean,
    ForeignKey,
    Text,
    select,
    func,
    and_,
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
    ColumnProperty,
    declarative_base,
    RelationshipProperty,
)
from sqlalchemy.sql import expression

from app.core.database.defaults import gen_ulid
from app.core.types import (
    UserId,
    UserRelationId,
    ImageId,
    PlaceId,
    PostId,
    PostSaveId,
    CommentId,
    PlaceDataId,
    PostLikeId,
)


class UserRelationType(enum.Enum):
    following = "following"
    blocked = "blocked"


Base: Any = declarative_base()


class UserRelationRow(Base):
    __tablename__ = "follow"

    id: UserRelationId = Column(UUID(as_uuid=True), primary_key=True, default=gen_ulid)
    from_user_id: UserId = Column(UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    to_user_id: UserId = Column(UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    relation: UserRelationType = Column(Enum(UserRelationType), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("from_user_id", "to_user_id", name="_from_user_to_user_uc"),
        Index("user_relation_to_user_id_relation_idx", to_user_id, relation),
        Index("user_relation_from_user_id_relation_idx", from_user_id, relation),
    )


class UserRow(Base):
    __tablename__ = "user"

    id: UserId = Column(UUID(as_uuid=True), primary_key=True, default=gen_ulid)
    uid = Column(Text, unique=True, nullable=False)  # Firebase id, maps to Firebase users
    username = Column(Text, unique=True, nullable=False)
    first_name = Column(Text, nullable=False)
    last_name = Column(Text, nullable=False)
    phone_number = Column(Text, unique=True, nullable=True)
    profile_picture_id: ImageId = Column(UUID(as_uuid=True), ForeignKey("image_upload.id"), unique=True, nullable=True)
    is_featured = Column(Boolean, nullable=False, server_default=false())
    is_admin = Column(Boolean, nullable=False, server_default=expression.false())
    deleted = Column(Boolean, nullable=False, server_default=expression.false())
    username_lower = Column(Text, Computed("LOWER(username)"), unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    posts: list["PostRow"] = relationship("PostRow", back_populates="user", cascade="all, delete", passive_deletes=True)

    profile_picture: "RelationshipProperty[Optional[ImageUploadRow]]" = relationship(
        "ImageUploadRow",
        primaryjoin=lambda: UserRow.profile_picture_id == ImageUploadRow.id,
    )
    profile_picture_url = association_proxy("profile_picture", "firebase_public_url")
    profile_picture_blob_name = association_proxy("profile_picture", "firebase_blob_name")

    # Computed column properties
    post_count: ColumnProperty
    follower_count: ColumnProperty
    following_count: ColumnProperty


class WaitlistRow(Base):
    __tablename__ = "waitlist"

    id: uuid.UUID = Column(UUID(as_uuid=True), primary_key=True, default=gen_ulid)
    phone_number = Column(Text, unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class InviteRow(Base):
    __tablename__ = "invite"

    id: uuid.UUID = Column(UUID(as_uuid=True), primary_key=True, default=gen_ulid)
    phone_number = Column(Text, unique=True, nullable=False)
    invited_by: UserId = Column(UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class FCMTokenRow(Base):
    __tablename__ = "fcm_token"

    id: uuid.UUID = Column(UUID(as_uuid=True), primary_key=True, default=gen_ulid)
    user_id: UserId = Column(UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    token = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (UniqueConstraint("user_id", "token", name="_user_token"),)


class UserPrefsRow(Base):
    __tablename__ = "preferences"

    id: uuid.UUID = Column(UUID(as_uuid=True), primary_key=True, default=gen_ulid)
    user_id: UserId = Column(UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    follow_notifications = Column(Boolean, nullable=False, server_default=true())
    post_liked_notifications = Column(Boolean, nullable=False, server_default=true())
    comment_notifications = Column(Boolean, nullable=False, server_default=true())
    comment_liked_notifications = Column(Boolean, nullable=False, server_default=true())
    searchable_by_phone_number = Column(Boolean, nullable=False, server_default=true())
    post_notifications = Column(Boolean, nullable=False, server_default=true())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    user: "RelationshipProperty[UserRow]" = relationship("UserRow")


class CategoryRow(Base):
    __tablename__ = "category"

    name = Column(Text, primary_key=True)


class PlaceRow(Base):
    __tablename__ = "place"

    id: PlaceId = Column(UUID(as_uuid=True), primary_key=True, default=gen_ulid)
    name = Column(Text, nullable=False)

    # Latitude and longitude of the place
    # This might be the entrance of the place, the most visited location, etc.
    # NOT necessarily the geometric centroid of the place
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

    # Computed column for postgis, don't manually modify; modify the above columns instead
    location: Any = Column(
        Geography(geometry_type="POINT", srid=4326, spatial_index=False),
        Computed("ST_MakePoint(longitude, latitude)::geography"),
        nullable=False,
    )

    # Only set in case estimated place data is incorrect
    verified_place_data: PlaceDataId = Column(UUID(as_uuid=True), ForeignKey("place_data.id"), nullable=True)

    region_name: ColumnProperty

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Only want one row per (name, latitude, longitude)
    __table_args__ = (
        UniqueConstraint("name", "latitude", "longitude", name="_place_name_location"),
        Index("idx_place_location", location, postgresql_using="gist"),
    )


class PlaceDataRow(Base):
    """
    Crowd-sourced place data.
    """

    __tablename__ = "place_data"

    id: PlaceDataId = Column(UUID(as_uuid=True), primary_key=True, default=gen_ulid)
    user_id: UserId = Column(UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    place_id: PlaceId = Column(UUID(as_uuid=True), ForeignKey("place.id", ondelete="CASCADE"), nullable=False)

    # Region that describes the boundary of the place
    # Used to deduplicate places
    region_center_lat = Column(Float, nullable=True)
    region_center_long = Column(Float, nullable=True)
    radius_meters = Column(Float, nullable=True)

    # Additional data like business url, phone number, point of interest categories, etc.
    additional_data = Column(JSONB, nullable=True)

    # Computed column for postgis, don't manually modify; modify the above columns instead
    region_center: Any = Column(
        Geography(geometry_type="POINT", srid=4326, spatial_index=False),
        Computed("ST_MakePoint(region_center_long, region_center_lat)::geography"),
    )
    region: Any = Column(
        Geography(geometry_type="POLYGON", srid=4326, spatial_index=False),
        Computed("ST_Buffer(ST_MakePoint(region_center_long, region_center_lat)::geography, radius_meters, 100)"),
    )
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    place: "RelationshipProperty[PlaceRow]" = relationship(
        "PlaceRow", primaryjoin=lambda: PlaceDataRow.place_id == PlaceRow.id
    )

    # Only want one row per (user, place) pair
    __table_args__ = (
        UniqueConstraint("user_id", "place_id", name="_place_data_user_place_uc"),
        Index("idx_place_data_region", region, postgresql_using="gist"),
        Index("idx_place_data_region_center", region_center, postgresql_using="gist"),
    )


class PostRow(Base):
    __tablename__ = "post"

    id: PostId = Column(UUID(as_uuid=True), primary_key=True, default=gen_ulid)
    user_id: UserId = Column(UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    place_id: PlaceId = Column(UUID(as_uuid=True), ForeignKey("place.id"), nullable=False)
    category = Column(Text, ForeignKey("category.name"), nullable=False)
    # If a custom location is selected for an existing place
    custom_latitude = Column(Float, nullable=True)
    custom_longitude = Column(Float, nullable=True)
    custom_location: Any = Column(
        Geography(geometry_type="POINT", srid=4326, spatial_index=False),
        Computed("ST_MakePoint(custom_longitude, custom_latitude)::geography"),
        nullable=True,
    )

    content = Column(Text, nullable=False)
    image_id: Optional[ImageId] = Column(UUID(as_uuid=True), ForeignKey("image_upload.id"), unique=True, nullable=True)
    deleted = Column(Boolean, nullable=False, server_default=expression.false())
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    user: "RelationshipProperty[UserRow]" = relationship("UserRow")
    place: "RelationshipProperty[PlaceRow]" = relationship("PlaceRow")
    image: "RelationshipProperty[Optional[ImageUploadRow]]" = relationship("ImageUploadRow")

    image_url = association_proxy("image", "firebase_public_url")
    image_blob_name = association_proxy("image", "firebase_blob_name")

    # Column properties
    like_count: ColumnProperty
    comment_count: ColumnProperty

    # Only want one row per (user, place) pair for all non-deleted posts
    user_place_uc = "_posts_user_place_uc"
    __table_args__ = (
        Index(
            user_place_uc,
            "user_id",
            "place_id",
            unique=True,
            postgresql_where=(~deleted),
        ),
        Index("idx_post_custom_location", custom_location, postgresql_using="gist"),
    )


class PostLikeRow(Base):
    __tablename__ = "post_like"

    id: PostLikeId = Column(UUID(as_uuid=True), primary_key=True, default=gen_ulid)
    user_id: UserId = Column(UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    post_id: PostId = Column(UUID(as_uuid=True), ForeignKey("post.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    liked_by: "RelationshipProperty[UserRow]" = relationship("UserRow")

    # Only want one row per (user, post) pair
    __table_args__ = (
        UniqueConstraint("user_id", "post_id", name="_post_like_user_post_uc"),
        Index("post_like_post_id_idx", post_id),
    )


class PostSaveRow(Base):
    __tablename__ = "post_save"

    id: PostSaveId = Column(UUID(as_uuid=True), primary_key=True, default=gen_ulid)
    user_id: UserId = Column(UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    post_id: PostId = Column(UUID(as_uuid=True), ForeignKey("post.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    saved_by: "RelationshipProperty[UserRow]" = relationship("UserRow")

    # Only want one row per (user, post) pair
    __table_args__ = (
        UniqueConstraint("user_id", "post_id", name="_saved_post_user_post_uc"),
        Index("saved_post_user_id_idx", user_id),
    )


# Comments
class CommentLikeRow(Base):
    __tablename__ = "comment_like"

    id: uuid.UUID = Column(UUID(as_uuid=True), primary_key=True, default=gen_ulid)
    user_id: UserId = Column(UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    comment_id: CommentId = Column(UUID(as_uuid=True), ForeignKey("comment.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Only want one row per (user, comment) pair
    __table_args__ = (UniqueConstraint("user_id", "comment_id", name="_comment_like_user_post_uc"),)


class CommentRow(Base):
    __tablename__ = "comment"

    id: CommentId = Column(UUID(as_uuid=True), primary_key=True, default=gen_ulid)
    user_id: UserId = Column(UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    post_id: PostId = Column(UUID(as_uuid=True), ForeignKey("post.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    deleted = Column(Boolean, nullable=False, server_default=expression.false())

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    user: "RelationshipProperty[UserRow]" = relationship("UserRow")

    # Column property
    like_count: ColumnProperty

    __table_args__ = (Index("comment_post_id_idx", post_id),)


# Reports


class PostReportRow(Base):
    __tablename__ = "post_report"
    id: uuid.UUID = Column(UUID(as_uuid=True), primary_key=True, default=gen_ulid)
    post_id: PostId = Column(UUID(as_uuid=True), ForeignKey("post.id", ondelete="CASCADE"), nullable=False)
    reported_by_user_id: UserId = Column(UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    post: "RelationshipProperty[PostRow]" = relationship("PostRow")
    reported_by: "RelationshipProperty[UserRow]" = relationship("UserRow")

    # Can only report a post once
    __table_args__ = (UniqueConstraint("post_id", "reported_by_user_id", name="_report_post_user_uc"),)


class ImageUploadRow(Base):
    __tablename__ = "image_upload"

    id: ImageId = Column(UUID(as_uuid=True), primary_key=True, default=gen_ulid)
    user_id: UserId = Column(UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    firebase_blob_name = Column(Text, nullable=True)  # Set after creating the row in db
    firebase_public_url = Column(Text, nullable=True)  # Set after creating the row in db
    used = Column(Boolean, nullable=False, server_default=false())  # Prevent using the same image in different places
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class FeedbackRow(Base):
    __tablename__ = "feedback"
    id: uuid.UUID = Column(UUID(as_uuid=True), primary_key=True, default=gen_ulid)
    user_id: UserId = Column(UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    contents = Column(Text, nullable=False)
    follow_up = Column(Boolean, nullable=False, server_default=expression.false())
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    user: "RelationshipProperty[UserRow]" = relationship("UserRow")


# Column properties

# Users
post_alias = aliased(PostRow)
relation_alias = aliased(UserRelationRow)
post_like_alias = aliased(PostLikeRow)

UserRow.post_count = column_property(
    select([func.count()]).where(and_(post_alias.user_id == UserRow.id, ~post_alias.deleted)).scalar_subquery(),
    deferred=True,
)

UserRow.follower_count = column_property(
    select([func.count()])
    .select_from(relation_alias)
    .where(
        and_(
            relation_alias.to_user_id == UserRow.id,
            relation_alias.relation == UserRelationType.following,
        )
    )
    .scalar_subquery(),
    deferred=True,
)

UserRow.following_count = column_property(
    select([func.count()])
    .select_from(relation_alias)
    .where(
        and_(
            relation_alias.from_user_id == UserRow.id,
            relation_alias.relation == UserRelationType.following,
        )
    )
    .scalar_subquery(),
    deferred=True,
)

# Posts
PostRow.like_count = column_property(
    select([func.count()]).select_from(post_like_alias).where(PostRow.id == post_like_alias.post_id).scalar_subquery(),
    deferred=True,
)

PostRow.comment_count = column_property(
    select([func.count()])
    .select_from(CommentRow)
    .where(and_(PostRow.id == CommentRow.post_id, ~CommentRow.deleted))
    .scalar_subquery(),
    deferred=True,
)

# Comments
CommentRow.like_count = column_property(
    select([func.count()])
    .select_from(CommentLikeRow)
    .where(CommentRow.id == CommentLikeRow.comment_id)
    .scalar_subquery(),
    deferred=True,
)

# PlaceRow data
PlaceRow.region_name = column_property(
    select([PlaceDataRow.additional_data["locality"]])
    .select_from(PlaceDataRow)
    .where((PlaceRow.id == PlaceDataRow.place_id) & (PlaceDataRow.additional_data["locality"].isnot(None)))
    .limit(1)
    .scalar_subquery(),
    deferred=False,
)
