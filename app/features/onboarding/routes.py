from fastapi import APIRouter, BackgroundTasks, Depends
import sqlalchemy as sa

from sqlalchemy.dialects import postgresql as pg
from sqlalchemy.ext.asyncio import AsyncSession
from app import tasks
from app.core.database.engine import get_db
from app.core.database.models import PlaceSaveRow, PostRow, UserRow
from app.core.types import SimpleResponse

from app.features.onboarding.types import CreateMultiRequest, OnboardingCity, PlaceTilePage
from app.features.users.dependencies import get_caller_user
from app.features.users.entities import InternalUser

from app.features.onboarding.data import featured_posts_by_city
from app.utils import get_logger

router = APIRouter(tags=["onboarding"])
log = get_logger(__name__)


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
        log.error("Error when onboarding user (request=%s)", request.json(), exc_info=e)
        return SimpleResponse(success=False)
