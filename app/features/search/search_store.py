import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.helpers import eager_load_user_options
from app.core.database.models import UserRow


class SearchStore:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def search_users(self, keyword: str) -> list[UserRow]:
        keyword = keyword.replace("\\", "\\\\").replace("_", "\\_").replace("%", "\\%")
        ilike = f"{keyword}%"
        query = (
            sa.select(UserRow)
            .options(*eager_load_user_options())
            .where(
                UserRow.username_lower.ilike(ilike)
                | sa.func.concat(UserRow.first_name, " ", UserRow.last_name).ilike(ilike)
            )
            .where(~UserRow.deleted)
        )
        query = query.order_by(UserRow.follower_count.desc()).limit(25)
        result = await self.db.execute(query)
        return result.scalars().all()  # type: ignore
