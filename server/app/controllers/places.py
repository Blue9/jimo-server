import uuid
from typing import Optional

from sqlalchemy import func, asc, and_, false, exists
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import schemas
from app.controllers import utils
from app.controllers.users import get_following
from app.models import models


def save_place_data(db: Session, user: models.User, place: models.Place,
                    region: schemas.place.Region) -> models.PlaceData:
    """Save the given place data to the database."""
    # TODO(gmekkat): Add additional data
    place_data = models.PlaceData(place_id=place.id, user_id=user.id, region_center_lat=region.latitude,
                                  region_center_long=region.longitude, radius_meters=region.radius,
                                  additional_data=None)
    try:
        db.add(place_data)
        db.commit()
    except IntegrityError:
        db.rollback()
        # Place data exists, just update it
        existing: models.PlaceData = db.query(models.PlaceData).filter(
            and_(models.PlaceData.user_id == user.id, models.PlaceData.place_id == place.id)).first()
        # It's unlikely, but if we delete the matching row before querying and after trying to insert,
        # existing could be None
        if existing is not None:
            existing.region_center_lat = place_data.region_center_lat
            existing.region_center_long = place_data.region_center_long
            existing.radius_meters = place_data.radius_meters
            existing.additional_data = place_data.additional_data
            db.commit()
    return place_data


def create_place(db: Session, request: schemas.place.MaybeCreatePlaceRequest) -> models.Place:
    """Create a place in the database with the given details."""
    place = models.Place(name=request.name, latitude=request.location.latitude, longitude=request.location.longitude)
    try:
        db.add(place)
        db.commit()
        return place
    except IntegrityError as e:
        db.rollback()
        if utils.is_unique_column_error(e, models.Place.external_id.key):
            raise ValueError("UUID collision")
        # else the place exists
        return db.query(models.Place).filter(
            and_(models.Place.name == request.name, models.Place.latitude == request.location.latitude,
                 models.Place.longitude == request.location.longitude)).first()


def get_place_or_create(db: Session, user: models.User, request: schemas.place.MaybeCreatePlaceRequest) -> models.Place:
    """Try to find a matching place for the request; otherwise create a new place.

    Note: A place has two components: a location and a region. The location is what appears on a user's map and serves
    no other purpose as of now. The region denotes the bounding box of the location.

    First, we use use the region radius that was passed in the request if provided. We then check if any place has the
    same name and is within this distance, returning one if it exists.

    Otherwise, we try to find a matching place within 10 meters.

    If we still cannot find an existing place, we create a new place.

    We also store the request's region (if provided) and additional data in place_data to improve data quality. Most of
    this data will probably be redundant since it only comes from Apple Maps at the moment.

    Note: if a malicious user passed in a very large radius, we would likely find a matching place and return one.
    Their malicious region data would get added to our place_data table and our radii could get skewed upward.

    Args:
        db: The database session.
        user: The user creating the place.
        request: The place details.

    Returns: The place object for the given request.
    """
    name = request.name
    location = request.location
    point = func.ST_GeographyFromText(f'POINT({location.longitude} {location.latitude})')

    # First check passed in region
    if request.region:
        radius = request.region.radius
        place = db.query(models.Place).filter(models.Place.name == name).filter(
            func.ST_Distance(point, models.Place.location) <= radius).order_by(
            asc(func.ST_Distance(point, models.Place.location))).first()
        if place:
            save_place_data(db, user, place, request.region)
            return place

    # Otherwise search a 10 meter radius
    place = db.query(models.Place).filter(models.Place.name == name).filter(
        func.ST_Distance(point, models.Place.location) <= 10).first()

    if place is None:
        place = create_place(db, request)
    if request.region:
        save_place_data(db, user, place, request.region)
    return place


def get_map(db: Session, user: models.User, limit: int) -> list[schemas.place.MapPin]:
    """Get the user's map view, returning up to the `limit` most recently posted places."""
    following_ids = [u.id for u in get_following(user)] + [user.id]
    response = db.query(models.Place.external_id.label("place_external_id"),
                        models.Place.latitude.label("place_latitude"),
                        models.Place.longitude.label("place_longitude"),
                        models.Place.name.label("place_name"),
                        models.Category.name.label("category"),
                        models.ImageUpload.firebase_public_url,
                        func.count(models.Post.id).over(partition_by=models.Place.id).label("num_mutual_posts")) \
        .select_from(models.Post) \
        .filter(models.Post.user_id.in_(following_ids), models.Post.deleted == false()) \
        .join(models.Place, models.Post.place_id == models.Place.id) \
        .join(models.Category, models.Post.category_id == models.Category.id) \
        .join(models.User, models.Post.user_id == models.User.id) \
        .join(models.ImageUpload, models.User.profile_picture_id == models.ImageUpload.id, isouter=True) \
        .order_by(models.Place.id, models.Post.created_at.desc()) \
        .distinct(models.Place.id) \
        .limit(limit) \
        .all()
    places = []
    for row in response:
        location = schemas.place.Location(latitude=row.place_latitude, longitude=row.place_longitude)
        place = schemas.place.Place(external_id=row.place_external_id, name=row.place_name, location=location)
        icon = schemas.place.MapPinIcon(category=row.category, icon_url=row.firebase_public_url,
                                        num_mutual_posts=row.num_mutual_posts)
        places.append(schemas.place.MapPin(place=place, icon=icon))
    return places


def get_place_icon(db: Session, user: models.User, place_id: uuid.UUID) -> schemas.place.MapPinIcon:
    following_ids = [u.id for u in get_following(user)] + [user.id]
    icon_details = db.query(func.count().over().label("num_mutual_posts"),
                            models.Category.name.label("category"),
                            models.ImageUpload.firebase_public_url.label("icon_url")) \
        .select_from(models.Post) \
        .join(models.Place, models.Post.place_id == models.Place.id) \
        .join(models.Category) \
        .join(models.User) \
        .join(models.ImageUpload, models.User.profile_picture_id == models.ImageUpload.id, isouter=True) \
        .filter(models.Place.external_id == place_id) \
        .filter(models.Post.user_id.in_(following_ids), models.Post.deleted == false()) \
        .order_by(models.Post.created_at.desc()) \
        .first()
    if icon_details is None:
        return schemas.place.MapPinIcon(num_mutual_posts=0)
    else:
        return schemas.place.MapPinIcon(category=icon_details.category, icon_url=icon_details.icon_url,
                                        num_mutual_posts=icon_details.num_mutual_posts)


def get_mutual_posts(db: Session, user: models.User, place_id: uuid.UUID,
                     limit: int) -> Optional[list[schemas.post.Post]]:
    following_ids = [u.id for u in get_following(user)] + [user.id]
    result = db.query(models.Post, exists()
                      .where(and_(models.post_like.c.post_id == models.Post.id,
                                  models.post_like.c.user_id == user.id))
                      .label("post_liked")) \
        .join(models.Place) \
        .filter(models.Place.external_id == place_id) \
        .filter(models.Post.user_id.in_(following_ids), models.Post.deleted == false()) \
        .order_by(models.Post.created_at.desc()) \
        .limit(limit) \
        .all()
    posts = []
    for post, is_post_liked in result:
        fields = schemas.post.ORMPost.from_orm(post).dict()
        posts.append(schemas.post.Post(**fields, liked=is_post_liked))
    return posts
