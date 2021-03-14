from sqlalchemy import Column, BigInteger, String, DateTime, Boolean, ForeignKey, Table, select, func, and_, Float, \
    Computed, UniqueConstraint, Index, false, text
from geoalchemy2 import Geography
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.orm import relationship, column_property, aliased
from sqlalchemy.sql import expression

from app.db.database import Base

follow = Table("follow", Base.metadata,
               Column("id", BigInteger, primary_key=True, nullable=False),
               Column("from_user_id", BigInteger, ForeignKey("user.id", ondelete="CASCADE")),
               Column("to_user_id", BigInteger, ForeignKey("user.id", ondelete="CASCADE")),
               Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()))


class User(Base):
    __tablename__ = "user"

    id = Column(BigInteger, primary_key=True, nullable=False)  # Database id, used for relationships
    external_id = Column(UUID(as_uuid=True), unique=True, nullable=False, server_default=text("gen_random_uuid()"))
    uid = Column(String, unique=True, nullable=False)  # Firebase id, maps to Firebase users
    username = Column(String(length=255), unique=True, nullable=False)
    first_name = Column(String(length=255), nullable=False)
    last_name = Column(String(length=255), nullable=False)
    phone_number = Column(String(length=255), unique=True, nullable=True)
    profile_picture_id = Column(BigInteger, ForeignKey("image_upload.id"), unique=True,
                                nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    deleted = Column(Boolean, nullable=False, server_default=expression.false())
    username_lower = Column(String(length=255), Computed("LOWER(username)"), unique=True, nullable=False)

    preferences = relationship("UserPrefs", uselist=False, back_populates="user", cascade="all, delete",
                               passive_deletes=True)

    posts: list["Post"] = relationship("Post", back_populates="user", cascade="all, delete", passive_deletes=True)

    following: list["User"] = relationship("User",
                                           secondary=follow,
                                           primaryjoin=id == follow.c.from_user_id,
                                           secondaryjoin=id == follow.c.to_user_id,
                                           cascade="all, delete",
                                           backref="followers")
    followers: list["User"] = None  # Computed with backref above

    profile_picture = relationship("ImageUpload", primaryjoin=lambda: User.profile_picture_id == ImageUpload.id)
    profile_picture_url = association_proxy("profile_picture", "firebase_public_url")

    # Computed column properties
    post_count = None
    follower_count = None
    following_count = None


class Waitlist(Base):
    __tablename__ = "waitlist"

    id = Column(BigInteger, primary_key=True, nullable=False)
    phone_number = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class Invite(Base):
    __tablename__ = "invite"

    id = Column(BigInteger, primary_key=True, nullable=False)
    phone_number = Column(String, unique=True, nullable=False)
    invited_by = Column(BigInteger, ForeignKey("user.id", ondelete="CASCADE"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class FCMToken(Base):
    __tablename__ = "fcm_token"

    id = Column(BigInteger, primary_key=True, nullable=False)
    user_id = Column(BigInteger, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    token = Column(String, nullable=False)

    __table_args__ = (UniqueConstraint("user_id", "token", name="_user_token"),)


class UserPrefs(Base):
    __tablename__ = "preferences"

    id = Column(BigInteger, primary_key=True, nullable=False)
    user_id = Column(BigInteger, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    post_notifications = Column(Boolean, nullable=False)
    follow_notifications = Column(Boolean, nullable=False)
    post_liked_notifications = Column(Boolean, nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    user = relationship("User", back_populates="preferences")


class Category(Base):
    __tablename__ = "category"

    id = Column(BigInteger, primary_key=True, nullable=False)
    name = Column(String, unique=True, nullable=False)


class Place(Base):
    __tablename__ = "place"

    id = Column(BigInteger, primary_key=True, nullable=False)
    external_id = Column(UUID(as_uuid=True), unique=True, nullable=False, server_default=text("gen_random_uuid()"))
    name = Column(String, nullable=False)

    # Latitude and longitude of the place
    # This might be the entrance of the place, the most visited location, etc.
    # NOT necessarily the geometric centroid of the place
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

    # Computed column for postgis, don't manually modify; modify the above columns instead
    location = Column(Geography(geometry_type="POINT", srid=4326),
                      Computed("ST_MakePoint(longitude, latitude)::geography"), nullable=False)

    # Only set in case estimated place data is incorrect
    verified_place_data = Column(BigInteger, ForeignKey("place.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Only want one row per (name, latitude, longitude)
    __table_args__ = (UniqueConstraint("name", "latitude", "longitude", name="_place_name_location"),)


class PlaceData(Base):
    """
    Crowd-sourced place data.
    """
    __tablename__ = "place_data"

    id = Column(BigInteger, primary_key=True, nullable=False)
    user_id = Column(BigInteger, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    place_id = Column(BigInteger, ForeignKey("place.id"), nullable=False)

    # Region that describes the boundary of the place
    # Used to deduplicate places
    region_center_lat = Column(Float, nullable=True)
    region_center_long = Column(Float, nullable=True)
    radius_meters = Column(Float, nullable=True)

    # Additional data like business url, phone number, point of interest categories, etc.
    additional_data = Column(JSONB, nullable=True)

    # Computed column for postgis, don't manually modify; modify the above columns instead
    region_center = Column(Geography(geometry_type="POINT", srid=4326),
                           Computed("ST_MakePoint(region_center_long, region_center_lat)::geography"))
    region = Column(Geography(geometry_type="POLYGON", srid=4326), Computed(
        "ST_Buffer(ST_MakePoint(region_center_long, region_center_lat)::geography, radius_meters, 100)"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    place = relationship("Place")

    # Only want one row per (user, place) pair
    __table_args__ = (UniqueConstraint("user_id", "place_id", name="_place_data_user_place_uc"),)


post_like = Table("post_like", Base.metadata,
                  Column("id", BigInteger, primary_key=True, nullable=False),
                  Column("user_id", BigInteger, ForeignKey("user.id", ondelete="CASCADE"), nullable=False),
                  Column("post_id", BigInteger, ForeignKey("post.id", ondelete="CASCADE"), nullable=False),
                  Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()))


class Post(Base):
    __tablename__ = "post"

    id = Column(BigInteger, primary_key=True, nullable=False)
    external_id = Column(UUID(as_uuid=True), unique=True, nullable=False, server_default=text("gen_random_uuid()"))
    user_id = Column(BigInteger, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    place_id = Column(BigInteger, ForeignKey("place.id"), nullable=False)
    category_id = Column(BigInteger, ForeignKey("category.id"), nullable=False)
    # If a custom location is selected for an existing place
    custom_latitude = Column(Float, nullable=True)
    custom_longitude = Column(Float, nullable=True)
    custom_location = Column(Geography(geometry_type="POINT", srid=4326),
                             Computed("ST_MakePoint(custom_longitude, custom_latitude)::geography"), nullable=True)

    content = Column(String, nullable=False)
    image_id = Column(BigInteger, ForeignKey("image_upload.id"), unique=True, nullable=True)
    deleted = Column(Boolean, nullable=False, server_default=expression.false())
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    user = relationship("User")
    place = relationship("Place")
    image = relationship("ImageUpload")
    _category = relationship("Category")
    likes = relationship("User", secondary=post_like, cascade="all, delete", passive_deletes=True)

    image_url = association_proxy("image", "firebase_public_url")
    category = association_proxy("_category", "name")

    # Column property
    like_count = None

    # Only want one row per (user, place) pair for all non-deleted posts
    user_place_uc = "_posts_user_place_uc"
    __table_args__ = (Index(user_place_uc, "user_id", "place_id", unique=True, postgresql_where=(~deleted)),)


# Reports

class PostReport(Base):
    __tablename__ = "post_report"
    id = Column(BigInteger, primary_key=True, nullable=False)
    post_id = Column(BigInteger, ForeignKey("post.id", ondelete="CASCADE"), nullable=False)
    reported_by_user_id = Column(BigInteger, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    details = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Can only report a post once
    __table_args__ = (UniqueConstraint("post_id", "reported_by_user_id", name="_report_post_user_uc"),)


class ImageUpload(Base):
    __tablename__ = "image_upload"

    id = Column(BigInteger, primary_key=True, nullable=False)
    external_id = Column(UUID(as_uuid=True), unique=True, nullable=False, server_default=text("gen_random_uuid()"))
    user_id = Column(BigInteger, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    firebase_blob_name = Column(String, nullable=True)  # Set after creating the row in db
    firebase_public_url = Column(String, nullable=True)  # Set after creating the row in db
    used = Column(Boolean, nullable=False, server_default=false())  # Prevent using the same image in different places
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class Feedback(Base):
    __tablename__ = "feedback"
    id = Column(BigInteger, primary_key=True, nullable=False)
    user_id = Column(BigInteger, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    contents = Column(String, nullable=False)
    follow_up = Column(Boolean, nullable=False, server_default=expression.false())


# Column properties

# Users
other_user = aliased(User)
User.post_count = column_property(select([func.count()]).where(and_(Post.user_id == User.id, Post.deleted == false())),
                                  deferred=True)
User.follower_count = column_property(
    select([func.count()]).select_from(follow.join(other_user, follow.c.from_user_id == other_user.id)).where(
        and_(follow.c.to_user_id == User.id, other_user.deleted == false())), deferred=True)

User.following_count = column_property(
    select([func.count()]).select_from(follow.join(other_user, follow.c.to_user_id == other_user.id)).where(
        and_(follow.c.from_user_id == User.id, other_user.deleted == false())), deferred=True)

# Posts
Post.like_count = column_property(
    select([func.count()]).select_from(post_like.join(User)).where(
        and_(Post.id == post_like.c.post_id, User.deleted == false())), deferred=True)
