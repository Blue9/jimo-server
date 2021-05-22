import enum

from sqlalchemy import Column, Enum, DateTime, Boolean, ForeignKey, Text, select, func, and_, Float, Computed, \
    UniqueConstraint, Index, false
from geoalchemy2 import Geography
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.orm import relationship, column_property, aliased
from sqlalchemy.sql import expression

from app.db.database import Base
from app.models.defaults import gen_ulid


class UserRelationType(enum.Enum):
    following = "following"
    blocked = "blocked"


class UserRelation(Base):
    __tablename__ = "follow"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_ulid)
    from_user_id = Column(UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    to_user_id = Column(UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    relation = Column(Enum(UserRelationType), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (UniqueConstraint("from_user_id", "to_user_id", name="_from_user_to_user_uc"),
                      Index("user_relation_to_user_id_relation_idx", to_user_id, relation),
                      Index("user_relation_from_user_id_relation_idx", from_user_id, relation))


class User(Base):
    __tablename__ = "user"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_ulid)
    uid = Column(Text, unique=True, nullable=False)  # Firebase id, maps to Firebase users
    username = Column(Text, unique=True, nullable=False)
    first_name = Column(Text, nullable=False)
    last_name = Column(Text, nullable=False)
    phone_number = Column(Text, unique=True, nullable=True)
    profile_picture_id = Column(UUID(as_uuid=True), ForeignKey("image_upload.id"), unique=True, nullable=True)
    is_featured = Column(Boolean, nullable=False, server_default=false())
    is_admin = Column(Boolean, nullable=False, server_default=expression.false())
    deleted = Column(Boolean, nullable=False, server_default=expression.false())
    username_lower = Column(Text, Computed("LOWER(username)"), unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    preferences = relationship("UserPrefs", uselist=False, back_populates="user", cascade="all, delete",
                               passive_deletes=True)

    posts: list["Post"] = relationship("Post", back_populates="user", cascade="all, delete", passive_deletes=True)

    profile_picture = relationship("ImageUpload", primaryjoin=lambda: User.profile_picture_id == ImageUpload.id)
    profile_picture_url = association_proxy("profile_picture", "firebase_public_url")
    profile_picture_blob_name = association_proxy("profile_picture", "firebase_blob_name")

    # Computed column properties
    post_count = None
    follower_count = None
    following_count = None


class Waitlist(Base):
    __tablename__ = "waitlist"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_ulid)
    phone_number = Column(Text, unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class Invite(Base):
    __tablename__ = "invite"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_ulid)
    phone_number = Column(Text, unique=True, nullable=False)
    invited_by = Column(UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class FCMToken(Base):
    __tablename__ = "fcm_token"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_ulid)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    token = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (UniqueConstraint("user_id", "token", name="_user_token"),)


class UserPrefs(Base):
    __tablename__ = "preferences"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_ulid)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    post_notifications = Column(Boolean, nullable=False)
    follow_notifications = Column(Boolean, nullable=False)
    post_liked_notifications = Column(Boolean, nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    user = relationship("User", back_populates="preferences")


class Category(Base):
    __tablename__ = "category"

    name = Column(Text, primary_key=True)


class Place(Base):
    __tablename__ = "place"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_ulid)
    name = Column(Text, nullable=False)

    # Latitude and longitude of the place
    # This might be the entrance of the place, the most visited location, etc.
    # NOT necessarily the geometric centroid of the place
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

    # Computed column for postgis, don't manually modify; modify the above columns instead
    location = Column(Geography(geometry_type="POINT", srid=4326, spatial_index=False),
                      Computed("ST_MakePoint(longitude, latitude)::geography"), nullable=False)

    # Only set in case estimated place data is incorrect
    verified_place_data = Column(UUID(as_uuid=True), ForeignKey("place_data.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Only want one row per (name, latitude, longitude)
    __table_args__ = (UniqueConstraint("name", "latitude", "longitude", name="_place_name_location"),
                      Index("idx_place_location", location, postgresql_using="gist"))


class PlaceData(Base):
    """
    Crowd-sourced place data.
    """
    __tablename__ = "place_data"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_ulid)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    place_id = Column(UUID(as_uuid=True), ForeignKey("place.id", ondelete="CASCADE"), nullable=False)

    # Region that describes the boundary of the place
    # Used to deduplicate places
    region_center_lat = Column(Float, nullable=True)
    region_center_long = Column(Float, nullable=True)
    radius_meters = Column(Float, nullable=True)

    # Additional data like business url, phone number, point of interest categories, etc.
    additional_data = Column(JSONB, nullable=True)

    # Computed column for postgis, don't manually modify; modify the above columns instead
    region_center = Column(Geography(geometry_type="POINT", srid=4326, spatial_index=False),
                           Computed("ST_MakePoint(region_center_long, region_center_lat)::geography"))
    region = Column(Geography(geometry_type="POLYGON", srid=4326, spatial_index=False), Computed(
        "ST_Buffer(ST_MakePoint(region_center_long, region_center_lat)::geography, radius_meters, 100)"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    place = relationship("Place", primaryjoin=lambda: PlaceData.place_id == Place.id)

    # Only want one row per (user, place) pair
    __table_args__ = (UniqueConstraint("user_id", "place_id", name="_place_data_user_place_uc"),
                      Index("idx_place_data_region", region, postgresql_using="gist"),
                      Index("idx_place_data_region_center", region_center, postgresql_using="gist"))


class PostLike(Base):
    __tablename__ = "post_like"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_ulid)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    post_id = Column(UUID(as_uuid=True), ForeignKey("post.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Only want one row per (user, post) pair
    __table_args__ = (UniqueConstraint("user_id", "post_id", name="_post_like_user_post_uc"),
                      Index("post_like_post_id_idx", post_id))


class Post(Base):
    __tablename__ = "post"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_ulid)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    place_id = Column(UUID(as_uuid=True), ForeignKey("place.id"), nullable=False)
    category = Column(Text, ForeignKey("category.name"), nullable=False)
    # If a custom location is selected for an existing place
    custom_latitude = Column(Float, nullable=True)
    custom_longitude = Column(Float, nullable=True)
    custom_location = Column(Geography(geometry_type="POINT", srid=4326, spatial_index=False),
                             Computed("ST_MakePoint(custom_longitude, custom_latitude)::geography"), nullable=True)

    content = Column(Text, nullable=False)
    image_id = Column(UUID(as_uuid=True), ForeignKey("image_upload.id"), unique=True, nullable=True)
    deleted = Column(Boolean, nullable=False, server_default=expression.false())
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    user = relationship("User")
    place = relationship("Place")
    image = relationship("ImageUpload")

    image_url = association_proxy("image", "firebase_public_url")
    image_blob_name = association_proxy("image", "firebase_blob_name")

    # Column property
    like_count = None

    # Only want one row per (user, place) pair for all non-deleted posts
    user_place_uc = "_posts_user_place_uc"
    __table_args__ = (Index(user_place_uc, "user_id", "place_id", unique=True, postgresql_where=(~deleted)),
                      Index("idx_post_custom_location", custom_location, postgresql_using="gist"))


# Reports

class PostReport(Base):
    __tablename__ = "post_report"
    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_ulid)
    post_id = Column(UUID(as_uuid=True), ForeignKey("post.id", ondelete="CASCADE"), nullable=False)
    reported_by_user_id = Column(UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    post = relationship("Post")
    reported_by = relationship("User")

    # Can only report a post once
    __table_args__ = (UniqueConstraint("post_id", "reported_by_user_id", name="_report_post_user_uc"),)


class ImageUpload(Base):
    __tablename__ = "image_upload"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_ulid)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    firebase_blob_name = Column(Text, nullable=True)  # Set after creating the row in db
    firebase_public_url = Column(Text, nullable=True)  # Set after creating the row in db
    used = Column(Boolean, nullable=False, server_default=false())  # Prevent using the same image in different places
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class Feedback(Base):
    __tablename__ = "feedback"
    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_ulid)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    contents = Column(Text, nullable=False)
    follow_up = Column(Boolean, nullable=False, server_default=expression.false())
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    user = relationship("User")


# Column properties

# Users
post_alias = aliased(Post)

User.post_count = column_property(
    select([func.count()]).where(and_(post_alias.user_id == User.id, post_alias.deleted == false())).scalar_subquery(),
    deferred=True)

User.follower_count = column_property(
    select([func.count()]).select_from(UserRelation).where(
        and_(UserRelation.to_user_id == User.id,
             UserRelation.relation == UserRelationType.following)).scalar_subquery(), deferred=True)

User.following_count = column_property(
    select([func.count()]).select_from(UserRelation).where(
        and_(UserRelation.from_user_id == User.id,
             UserRelation.relation == UserRelationType.following)).scalar_subquery(), deferred=True)

# Posts
Post.like_count = column_property(select([func.count()]).select_from(PostLike).where(
    and_(Post.id == PostLike.post_id)).scalar_subquery(), deferred=True)
