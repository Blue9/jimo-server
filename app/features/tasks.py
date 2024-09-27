from app import tasks
from app.core.database.engine import get_db_context
from app.core.types import UserId
from app.features.users.entities import InternalUser
from app.features.users.user_store import UserStore


# Note: This makes N queries, can optimize later
async def notify_many_followed(user: InternalUser, followed_users: list[UserId]):
    async with get_db_context() as db:
        user_store = UserStore(db)
        for followed in followed_users:
            prefs = await user_store.get_user_preferences(followed)
            if prefs.follow_notifications:
                await tasks.notify_follow(followed, followed_by=user)
