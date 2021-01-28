from sqlalchemy import func, asc
from sqlalchemy.orm import Session

from app.controllers import utils
from app.models.models import Place, PlaceData
from app.models.request_schemas import MaybeCreatePlaceRequest
from app.models.schemas import Region


def save_place_data(db: Session, place: Place, region: Region) -> PlaceData:
    """Save the given place data to the database."""
    # TODO(gmekkat): Add additional data
    place_data = PlaceData(place_id=place.id, region_center_lat=region.latitude,
                           region_center_long=region.longitude, radius_meters=region.radius, additional_data=None)
    db.add(place_data)
    db.commit()
    return place_data


def create_place(db: Session, request: MaybeCreatePlaceRequest) -> Place:
    """Create a place in the database with the given details."""
    build_place = lambda url_id: Place(urlsafe_id=url_id, name=request.name, latitude=request.location.latitude,
                                       longitude=request.location.longitude)
    new_place = utils.add_with_urlsafe_id(db, build_place)
    return new_place


def get_place_or_create(db: Session, request: MaybeCreatePlaceRequest) -> Place:
    """Try to find a matching place for the request; otherwise create a new place.

    Note: A place has two components: a location and a region. The location is what appears on a user's map and serves
    no other purpose as of now. The region denotes the bounding box of the location.

    First, we use use the region radius that was passed in the request if provided. We then check if any place has the
    same name and is within this distance, returning one if it exists.

    Otherwise, we try to find a matching place within 10 meters.

    If we still cannot find an existing place, we create a new place.

    We ALSO store the request's region (if provided) and additional data in place_data to improve data quality. Most of
    this data will probably be redundant since it only comes from Apple Maps at the moment.

    Note: if a malicious user passed in a very large radius, we would likely find a matching place and return one.
    Their malicious region data would get added to our place_data table and our radii could get skewed upward.

    Args:
        db: The database session.
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
        print(place)
        if place:
            save_place_data(db, place, request.region)
            return place

    # Otherwise, use the place_data table (don't do this for now)
    # This maps the place id to the median radius
    # radii = db.query(PlaceData.place_id,
    #                  func.ST_Centroid(func.ST_Union(cast(PlaceData.region_center, Geometry))).label('region_center'),
    #                  func.percentile_cont(0.5).within_group(PlaceData.radius_meters).label('radius')).group_by(
    #     PlaceData.place_id).subquery()
    #
    # place = db.query(Place).filter(Place.name == name).join(radii).filter(
    #     func.ST_Distance(point, radii.c.region_center) <= radii.c.radius).order_by(
    #     asc(func.ST_Distance(point, radii.c.region_center))).first()

    # Search a 10 meter radius
    place = db.query(Place).filter(Place.name == name).filter(func.ST_Distance(point, Place.location) <= 10).first()

    if place is None:
        place = create_place(db, request)
    if request.region:
        save_place_data(db, place, request.region)
    return place
