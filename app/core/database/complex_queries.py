import sqlalchemy as sa
from sqlalchemy import func

from app.features.places.entities import Region
from app.core.types import UserId, PlaceId
from app.core.database.models import (
    UserRelationRow,
    UserRelationType,
    PlaceRow,
    PostRow,
    ImageUploadRow,
    UserRow,
)
from app.features.map.filters import MapFilter, CategoryFilter


def get_suggested_users_query(user_id: UserId, limit: int) -> sa.sql.Select:
    """
    How this is computed:
    We first retrieve the list of followers for user_id. We then retrieve the list of users that the followers follow,
    minus the users that the given user is already following. This list is then sorted by the # of "mutual followers."
    """
    cte = (
        sa.select(UserRelationRow.to_user_id.label("id"))
        .select_from(UserRelationRow)
        .where(
            UserRelationRow.from_user_id == user_id,
            UserRelationRow.relation == UserRelationType.following,
        )
        .cte("already_followed")
    )
    return (
        sa.select(UserRelationRow.to_user_id, func.count(UserRelationRow.to_user_id))
        .select_from(UserRelationRow)
        .join(cte, cte.c.id == UserRelationRow.from_user_id)
        .where(UserRelationRow.to_user_id.notin_(sa.select(cte.c.id)))
        .where(UserRelationRow.to_user_id != user_id)
        .group_by(UserRelationRow.to_user_id)
        .order_by(func.count(UserRelationRow.to_user_id).desc())
        .limit(limit)
    )


def map_v3_query(region: Region, map_filter: MapFilter, category_filter: CategoryFilter, limit: int) -> sa.sql.Select:
    center = func.ST_GeographyFromText(f"POINT({region.longitude} {region.latitude})")
    query = (
        sa.select(
            PlaceRow.id,
            PlaceRow.latitude,
            PlaceRow.longitude,
            PostRow.category,
            ImageUploadRow.firebase_public_url,
            PostRow.user_id,
        )
        .select_from(PlaceRow)
        .join(PostRow, PostRow.place_id == PlaceRow.id)
        .join(UserRow, UserRow.id == PostRow.user_id)
        .join(
            ImageUploadRow,
            ImageUploadRow.id == UserRow.profile_picture_id,
            isouter=True,
        )
        .where(func.ST_Distance(center, PlaceRow.location) <= region.radius)
        .where(~UserRow.deleted)
        .where(~PostRow.deleted)
    )
    query = map_filter.apply(query)
    query = category_filter.apply(query)
    return query.where(~PostRow.deleted).order_by(PostRow.id.desc()).limit(limit)


def posts_for_pin_v3_query(
    place_id: PlaceId,
    user_filter: MapFilter,
    category_filter: CategoryFilter,
    limit: int,
) -> sa.sql.Select:
    query = sa.select(PostRow.id).where(PostRow.place_id == place_id).where(~PostRow.deleted)
    query = user_filter.apply(query)
    query = category_filter.apply(query)
    return query.order_by(PostRow.id.desc()).limit(limit)
