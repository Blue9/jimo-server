from fastapi import APIRouter, BackgroundTasks, Depends
import sqlalchemy as sa

from sqlalchemy.dialects import postgresql as pg
from sqlalchemy.ext.asyncio import AsyncSession
from app import tasks
from app.core.database.engine import get_db
from app.core.database.models import PlaceSaveRow, PostRow, UserRow
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
            place_id="017e31d8-9af6-31b9-c222-3e72f5986a6b",
            name="John's of Bleecker Street",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/4iDCYxpFLlgHHfcD2aP4Gl8iZKI2/0181ca57-9ed6-4d9b-527a-612aab05de43.jpg",
            category="food",
            description="",
        ),
        PlaceTile.construct(
            place_id="017f027c-03bb-e1fa-77d9-3563ce22052f",
            name="The Museum of Modern Art",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/IdH92jA12cNbWBCLEzX6tSfKQdz1/0180156b-6da5-fc9d-eb4d-42551153a87c.jpg",
            category="activity",
            description="",
        ),
        PlaceTile.construct(
            place_id="017948bc-6c60-c38e-c158-b518225d322d",
            name="Katz's Delicatessen",
            image_url="https://storage.googleapis.com/goodplaces-app.appspot.com/images/Bz1LawiaYqcziu7aZhRUbjLhM9K2/017b2197-5d70-0b2a-0bdd-1765f0bdb7e4.jpg",
            category="food",
            description="",
        ),
    ]
}


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
    # TODO: store onboarded_at in users table
    posts = request.posts
    saves = request.saves
    post_inserts = [
        pg.insert(PostRow)
        .values(user_id=user.id, place_id=post.place_id, content="", category=post.category, stars=post.stars)
        .on_conflict_do_update(
            index_elements=["user_id", "place_id"], set_={"category": post.category, "stars": post.stars}
        )
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
        await db.execute(
            sa.update(UserRow)
            .where(UserRow.id == user.id)
            .values(onboarded_at=sa.func.now(), onboarded_city=request.city)
        )
        await db.commit()
        return SimpleResponse(success=True)
    except Exception as e:
        await db.rollback()
        return SimpleResponse(success=False)
