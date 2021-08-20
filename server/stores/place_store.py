import uuid
from typing import Optional

from sqlalchemy import select, func, asc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import schemas
from stores import utils
from models import models


class PlaceStore:
    def __init__(self, db: Session):
        self.db = db

    # Queries

    def get_map(self, user_id: uuid.UUID, limit: int = 1000) -> list[schemas.place.MapPin]:
        """Get the user's map view, returning up to the `limit` most recently posted places."""
        following_ids = select(models.UserRelation.to_user_id).where(
            (models.UserRelation.from_user_id == user_id) & (
                models.UserRelation.relation == models.UserRelationType.following))
        query = select(models.Place.id.label("place_id"),
                       models.Place.latitude.label("place_latitude"),
                       models.Place.longitude.label("place_longitude"),
                       models.Place.name.label("place_name"),
                       models.Post.category.label("category"),
                       models.ImageUpload.firebase_public_url,
                       func.count(models.Post.id).over(partition_by=models.Place.id).label("num_mutual_posts")) \
            .select_from(models.Post) \
            .where(models.Post.user_id.in_(following_ids) | (models.Post.user_id == user_id)) \
            .where(~models.Post.deleted) \
            .join(models.Place, models.Post.place_id == models.Place.id) \
            .join(models.User, models.Post.user_id == models.User.id) \
            .join(models.ImageUpload, models.User.profile_picture_id == models.ImageUpload.id, isouter=True) \
            .order_by(models.Place.id.desc(), models.Post.id.desc()) \
            .distinct(models.Place.id) \
            .limit(limit)
        response = self.db.execute(query).all()
        places = []
        for row in response:
            location = schemas.place.Location(latitude=row.place_latitude, longitude=row.place_longitude)
            place = schemas.place.Place(
                id=row.place_id,
                name=row.place_name,
                location=location
            )
            icon = schemas.place.MapPinIcon(category=row.category, icon_url=row.firebase_public_url,
                                            num_mutual_posts=row.num_mutual_posts)
            places.append(schemas.place.MapPin(place=place, icon=icon))
        return places

    def get_place_icon(self, user_id: uuid.UUID, place_id: uuid.UUID) -> schemas.place.MapPinIcon:
        following_ids = select(models.UserRelation.to_user_id).where(
            (models.UserRelation.from_user_id == user_id) & (
                models.UserRelation.relation == models.UserRelationType.following))
        icon_details_query = select(func.count().over().label("num_mutual_posts"),
                                    models.Post.category.label("category"),
                                    models.ImageUpload.firebase_public_url.label("icon_url")) \
            .select_from(models.Post) \
            .join(models.Place, models.Post.place_id == models.Place.id) \
            .join(models.User) \
            .join(models.ImageUpload, models.User.profile_picture_id == models.ImageUpload.id, isouter=True) \
            .where(models.Place.id == place_id) \
            .where(models.Post.user_id.in_(following_ids) | (models.Post.user_id == user_id)) \
            .where(~models.Post.deleted) \
            .order_by(models.Post.created_at.desc())
        icon_details = self.db.execute(icon_details_query).first()
        if icon_details is None:
            return schemas.place.MapPinIcon(num_mutual_posts=0)
        else:
            return schemas.place.MapPinIcon(category=icon_details.category, icon_url=icon_details.icon_url,
                                            num_mutual_posts=icon_details.num_mutual_posts)

    # Operations

    def create_place(self, request: schemas.place.MaybeCreatePlaceRequest) -> schemas.place.Place:
        """Create a place in the database with the given details."""
        place = models.Place(name=request.name, latitude=request.location.latitude,
                             longitude=request.location.longitude)
        try:
            self.db.add(place)
            self.db.commit()
            return schemas.place.Place.from_orm(place)
        except IntegrityError as e:
            self.db.rollback()
            if utils.is_unique_column_error(e, models.Place.id.key):
                raise ValueError("UUID collision")
            # else the place exists
            existing_place_query = select(models.Place) \
                .where(models.Place.name == request.name,
                       models.Place.latitude == request.location.latitude,
                       models.Place.longitude == request.location.longitude)
            existing_place = self.db.execute(existing_place_query).scalars().one()
            return schemas.place.Place.from_orm(existing_place)

    def get_place(self, request: schemas.place.MaybeCreatePlaceRequest) -> Optional[schemas.place.Place]:
        """Try to find a matching place for the request.

        Note: A place has two components: a location and a region. The location is what appears on a user's map and
        serves no other purpose as of now. The region denotes the bounding box of the location.

        First, we use use the region radius that was passed in the request if provided. We then check if any place has
        the same name and is within this distance, returning one if it exists.

        Otherwise, we try to find a matching place within 10 meters.

        Args:
            request: The place details.

        Returns: The place object for the given request if it exists.
        """
        name = request.name
        location = request.location
        point = func.ST_GeographyFromText(f'POINT({location.longitude} {location.latitude})')

        # First check passed in region
        if request.region:
            radius = request.region.radius
            place_query = select(models.Place).where(models.Place.name == name).where(
                func.ST_Distance(point, models.Place.location) <= radius).order_by(
                asc(func.ST_Distance(point, models.Place.location)))
            place = self.db.execute(place_query).scalars().first()
            if place:
                return schemas.place.Place.from_orm(place)

        # Otherwise search a 10 meter radius
        place_query = select(models.Place) \
            .where(models.Place.name == name) \
            .where(func.ST_Distance(point, models.Place.location) <= 10)
        place = self.db.execute(place_query).scalars().first()
        return schemas.place.Place.from_orm(place) if place else None

    def create_or_update_place_data(
        self,
        user_id: uuid.UUID,
        place_id: uuid.UUID,
        region: Optional[schemas.place.Region] = None,
        additional_data: Optional[schemas.place.AdditionalPlaceData] = None
    ) -> None:
        """Save the given place data to the database."""
        place_data = models.PlaceData(place_id=place_id, user_id=user_id)
        if region:
            place_data.region_center_lat = region.latitude
            place_data.region_center_long = region.longitude
            place_data.radius_meters = region.radius
        if additional_data:
            place_data.additional_data = additional_data.dict()
        try:
            self.db.add(place_data)
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            # Place data exists, just update it
            existing_query = select(models.PlaceData) \
                .where(models.PlaceData.user_id == user_id, models.PlaceData.place_id == place_id)
            existing: Optional[models.PlaceData] = self.db.execute(existing_query).scalars().first()
            # It's unlikely, but if we delete the matching row before querying and after trying to insert,
            # existing could be None
            if existing is not None:
                existing.region_center_lat = place_data.region_center_lat
                existing.region_center_long = place_data.region_center_long
                existing.radius_meters = place_data.radius_meters
                existing.additional_data = place_data.additional_data
                self.db.commit()
