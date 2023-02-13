from fastapi import APIRouter, BackgroundTasks, Depends
import sqlalchemy as sa

from sqlalchemy.dialects import postgresql as pg
from sqlalchemy.ext.asyncio import AsyncSession
from app import tasks
from app.core.database.engine import get_db
from app.core.database.models import PlaceSaveRow, PostRow
from app.core.types import PostId, SimpleResponse

from app.features.onboarding.types import CreateMultiRequest, OnboardingCity, PlaceTile, PlaceTilePage
from app.features.places.place_store import PlaceStore
from app.features.posts.post_store import PostStore
from app.features.stores import get_place_store, get_post_store, get_user_store
from app.features.users.dependencies import get_caller_user
from app.features.users.entities import InternalUser
from app.features.users.user_store import UserStore


router = APIRouter()


# TODO hardcoded for now, improve if we see usage
featured_posts_by_city: dict[OnboardingCity, list[PlaceTile]] = {
    OnboardingCity.NYC: [
        PlaceTile.construct(
            place_id="017b1704-b923-9c92-45ac-dd4fdd1415d8",
            name="JeJu Noodle Bar",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/37XYQ0zG49MXD6kXvCfNbM6cl3j2/017b1704-b518-4784-e6f6-ec9c47b0b630.jpg",
            category="food",
            description="",
        ),
        PlaceTile.construct(
            place_id="017a7e55-6f05-848c-bf89-a092c1c7fbed",
            name="Torishin",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/37XYQ0zG49MXD6kXvCfNbM6cl3j2/017a7e55-6b8d-d225-7bbd-911af2004306.jpg",
            category="food",
            description="",
        ),
    ]
}


@router.get("/cities", response_model=list[OnboardingCity])
def get_cities(_current_user: InternalUser = Depends(get_caller_user)):
    """Get available cities."""
    return [e for e in OnboardingCity]


@router.get("/places", response_model=PlaceTilePage)
def get_posts_for_city(
    city: OnboardingCity,
    _current_user: InternalUser = Depends(get_caller_user),
):
    """Get select posts for the given city."""
    places = featured_posts_by_city.get(city)
    if not places:
        places = featured_posts_by_city[OnboardingCity.NYC]
    return PlaceTilePage.construct(places=places)


@router.post("/places", response_model=SimpleResponse)
async def submit_onboarding_places(
    request: CreateMultiRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user: InternalUser = Depends(get_caller_user),
):
    posts = request.posts
    saves = request.saves
    post_inserts = [
        pg.insert(PostRow)
        .values(user_id=user.id, place_id=post.place_id, content="", category=post.category, stars=post.stars)
        .on_conflict_do_update(index_elements=["user_id", "place_id"], set_={"category": post.category, "stars": post.stars})
        for post in posts
    ]
    save_inserts = [
        pg.insert(PlaceSaveRow).values(user_id=user.id, place_id=save.place_id, note="").on_conflict_do_nothing()
        for save in saves
    ]
    background_tasks.add_task(tasks.slack_onboarding, user.username, request.city, len(posts), len(saves))
    try:
        for post_insert in post_inserts:
            await db.execute(post_insert)
        for save_insert in save_inserts:
            await db.execute(save_insert)
        await db.commit()
        return SimpleResponse(success=True)
    except Exception as e:
        await db.rollback()
        return SimpleResponse(success=False)
