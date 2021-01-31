from sqlalchemy import func, asc, and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.controllers import utils
from app.models.models import Place, PlaceData, User
from app.models.request_schemas import MaybeCreatePlaceRequest
from app.models.schemas import Region


def save_place_data(db: Session, user: User, place: Place, region: Region) -> PlaceData:
    """Save the given place data to the database."""
    # TODO(gmekkat): Add additional data
    place_data = PlaceData(place_id=place.id, user_id=user.id, region_center_lat=region.latitude,
                           region_center_long=region.longitude, radius_meters=region.radius, additional_data=None)
    try:
        db.add(place_data)
        db.commit()
    except IntegrityError:
        db.rollback()
        # Place data exists, just update it
        existing: PlaceData = db.query(PlaceData).filter(
            and_(PlaceData.user_id == user.id, PlaceData.place_id == place.id)).first()
        # It's unlikely, but if we delete the matching row before querying and after trying to insert,
        # existing could be None
        if existing is not None:
            existing.region_center_lat = place_data.region_center_lat
            existing.region_center_long = place_data.region_center_long
            existing.radius_meters = place_data.radius_meters
            existing.additional_data = place_data.additional_data
            db.commit()
    return place_data


def create_place(db: Session, request: MaybeCreatePlaceRequest) -> Place:
    """Create a place in the database with the given details."""
    build_place = lambda url_id: Place(urlsafe_id=url_id, name=request.name, latitude=request.location.latitude,
                                       longitude=request.location.longitude)
    try:
        return utils.add_with_urlsafe_id(db, build_place)
    except IntegrityError:
        return db.query(Place).filter(and_(Place.name == request.name, Place.latitude == request.location.latitude,
                                           Place.longitude == request.location.longitude)).first()


def get_place_or_create(db: Session, user: User, request: MaybeCreatePlaceRequest) -> Place:
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
        place = db.query(Place).filter(Place.name == name).filter(
            func.ST_Distance(point, Place.location) <= radius).order_by(
            asc(func.ST_Distance(point, Place.location))).first()
        if place:
            save_place_data(db, user, place, request.region)
            return place

    # Otherwise search a 10 meter radius
    place = db.query(Place).filter(Place.name == name).filter(func.ST_Distance(point, Place.location) <= 10).first()

    if place is None:
        place = create_place(db, request)
    if request.region:
        save_place_data(db, user, place, request.region)
    return place
