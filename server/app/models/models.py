from sqlalchemy import Column, BigInteger, String, DateTime, Boolean, ForeignKey, Table, select, func, and_, Float, \
    Computed
from geoalchemy2 import Geography
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.orm import relationship, column_property
from sqlalchemy.sql import expression

from app.database import Base

follow = Table("follow", Base.metadata,
               Column("from_user_id", BigInteger, ForeignKey("user.id", ondelete="CASCADE"), primary_key=True),
               Column("to_user_id", BigInteger, ForeignKey("user.id", ondelete="CASCADE"), primary_key=True),
               Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()))


class User(Base):
    __tablename__ = "user"

    id = Column(BigInteger, primary_key=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    username = Column(String(length=255), unique=True, nullable=False)
    first_name = Column(String(length=255), nullable=False)
    last_name = Column(String(length=255), nullable=False)
    profile_picture_url = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    private_account = Column(Boolean, nullable=False, server_default=expression.false())
    deactivated = Column(Boolean, nullable=False, server_default=expression.false())

    preferences = relationship("UserPrefs", uselist=False, back_populates="user", cascade="all, delete",
                               passive_deletes=True)

    posts = relationship("Post", back_populates="user", cascade="all, delete", passive_deletes=True)

    following: list["User"] = relationship("User",
                                           secondary=follow,
                                           primaryjoin=id == follow.c.from_user_id,
                                           secondaryjoin=id == follow.c.to_user_id,
                                           cascade="all, delete",
                                           backref="followers")
    followers: list["User"] = None  # Computed with backref above

    username_lower = Column(String(length=255), Computed("LOWER(username)"), unique=True, nullable=False)

    # Computed column properties
    post_count = None
    follower_count = None
    following_count = None


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


class Tag(Base):
    __tablename__ = "tag"

    id = Column(BigInteger, primary_key=True, nullable=False)
    name = Column(String, unique=True, nullable=False)


class Place(Base):
    __tablename__ = "place"

    id = Column(BigInteger, primary_key=True, nullable=False)
    urlsafe_id = Column(String, unique=True, nullable=False)
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
    posts = relationship("Post", back_populates="place")


class PlaceData(Base):
    """
    Crowd-sourced place data.
    """
    __tablename__ = "place_data"

    id = Column(BigInteger, primary_key=True, nullable=False)
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


post_tag = Table("post_tag", Base.metadata,
                 Column("post_id", BigInteger, ForeignKey("post.id", ondelete="CASCADE"), nullable=False),
                 Column("tag_id", BigInteger, ForeignKey("tag.id", ondelete="CASCADE"), nullable=False))

post_like = Table("post_like", Base.metadata,
                  Column("user_id", BigInteger, ForeignKey("user.id", ondelete="CASCADE"), nullable=False),
                  Column("post_id", BigInteger, ForeignKey("post.id", ondelete="CASCADE"), nullable=False),
                  Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()))


class Post(Base):
    __tablename__ = "post"

    id = Column(BigInteger, primary_key=True, nullable=False)
    urlsafe_id = Column(String, unique=True, nullable=False)
    user_id = Column(BigInteger, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    place_id = Column(BigInteger, ForeignKey("place.id"), nullable=False)
    category_id = Column(BigInteger, ForeignKey("category.id"), nullable=False)
    # If a custom location is selected for an existing place
    custom_latitude = Column(Float, nullable=True)
    custom_longitude = Column(Float, nullable=True)
    custom_location = Column(Geography(geometry_type="POINT", srid=4326),
                             Computed("ST_MakePoint(custom_longitude, custom_latitude)::geography"), nullable=True)

    content = Column(String, nullable=False)
    image_url = Column(String, nullable=True)
    deleted = Column(Boolean, nullable=False, server_default=expression.false())
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    user = relationship("User", back_populates="posts")
    place = relationship("Place", back_populates="posts")
    _category = relationship("Category")
    _tags = relationship("Tag", secondary=post_tag, cascade="all, delete", passive_deletes=True)
    likes = relationship("User", secondary=post_like, cascade="all, delete", passive_deletes=True)
    comments = relationship("Comment", back_populates="post")

    tags = association_proxy("_tags", "name")
    category = association_proxy("_category", "name")

    # Column property
    like_count = None
    comment_count = None


class Comment(Base):
    __tablename__ = "comment"
    id = Column(BigInteger, primary_key=True, nullable=False)
    urlsafe_id = Column(String, unique=True, nullable=False)
    user_id = Column(BigInteger, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    post_id = Column(BigInteger, ForeignKey("post.id", ondelete="CASCADE"), nullable=False)
    content = Column(String, nullable=False)
    deleted = Column(Boolean, nullable=False, server_default=expression.false())
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    user = relationship("User")
    post = relationship("Post", back_populates="comments")


# Column properties
follow_alias = follow.alias()
# The follow alias is necessary because the followers+following relationship will join on follow, so we need another
# name to refer to follow in this subquery.

User.post_count = column_property(select([func.count()]).where(Post.id == User.id), deferred=True)
User.follower_count = column_property(select([func.count()]).where(follow_alias.c.to_user_id == User.id), deferred=True)
User.following_count = column_property(
    select([func.count()]).where(follow_alias.c.from_user_id == User.id), deferred=True)

Post.like_count = column_property(select([func.count()]).where(Post.id == post_like.c.post_id))
Post.comment_count = column_property(
    select([func.count()]).where(and_(Post.id == Comment.post_id, Comment.deleted == expression.false())))
